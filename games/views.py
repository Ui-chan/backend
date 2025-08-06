from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import random
import uuid
import boto3
from botocore.exceptions import NoCredentialsError
import threading 
from django.conf import settings
import vertexai
from vertexai.preview.vision_models import ImageGenerationModel
from django.db import transaction
from django.utils import timezone
from users.models import User
from .models import GameSession, GameInteractionLog, FirstGameQuiz
from .serializers import *
import concurrent.futures # 멀티 스레딩을 위한 라이브러리 import

def upload_to_s3(image_bytes, bucket_name, object_name):
    s3_client = boto3.client('s3', aws_access_key_id=settings.AWS_ACCESS_KEY_ID, aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY, region_name=settings.AWS_S3_REGION_NAME)
    try:
        s3_client.put_object(Body=image_bytes, Bucket=bucket_name, Key=object_name, ContentType='image/png')
        url = f"https://{bucket_name}.s3.{settings.AWS_S3_REGION_NAME}.amazonaws.com/{object_name}"
        return url
    except Exception as e:
        print(f"S3 upload failed: {e}")
        return None

def generate_image_with_vertex_ai(prompt: str) -> str:
    try:
        vertexai.init(project=settings.GCP_PROJECT_ID, location=settings.GCP_LOCATION)
        model = ImageGenerationModel.from_pretrained("imagegeneration@005")
        detailed_prompt = f"A simple cartoon of a {prompt}, white background"
        images = model.generate_images(prompt=detailed_prompt, number_of_images=1, negative_prompt="text, words, realistic, photo, scary, complex, multiple objects")
        if not images:
            return None
        image_bytes = images[0]._image_bytes
        bucket_name = settings.AWS_STORAGE_BUCKET_NAME
        object_name = f"quiz-images/{prompt.replace(' ', '_')}_{uuid.uuid4().hex}.png"
        return upload_to_s3(image_bytes, bucket_name, object_name)
    except Exception as e:
        print(f"Vertex AI image generation failed for prompt '{prompt}': {e}")
        return None

def create_quiz_set(user_id):
    """AI를 사용하여 퀴즈 3개를 생성하고 DB에 저장하는 함수 (백그라운드 실행용)"""
    try:
        user = User.objects.get(pk=user_id)
        prompts_to_generate = []
        quiz_data_list = []
        item_list = {"사과": "apple", "자동차": "car", "오리": "duck", "바나나": "banana", "공": "ball", "집": "house", "강아지": "dog", "고양이": "cat"}
        available_items = list(item_list.keys())

        for _ in range(3):
            correct_item_ko = random.choice(available_items)
            wrong_items_ko = random.sample([item for item in available_items if item != correct_item_ko], 2)
            correct_item_en = item_list[correct_item_ko]
            quiz_data = {
                "prompt_text": f"Where is the {correct_item_en}?",
                "correct_answer": correct_item_ko,
                "correct_prompt": correct_item_en,
                "wrong_prompts": [item_list[wrong_items_ko[0]], item_list[wrong_items_ko[1]]],
                "wrong_names": wrong_items_ko
            }
            quiz_data_list.append(quiz_data)
            prompts_to_generate.append(quiz_data["correct_prompt"])
            prompts_to_generate.extend(quiz_data["wrong_prompts"])

        image_urls = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=9) as executor:
            results = executor.map(generate_image_with_vertex_ai, prompts_to_generate)
            image_urls = list(results)
        
        if not all(image_urls):
            print(f"User {user_id}의 이미지 생성 중 일부 실패")
            return

        url_index = 0
        for quiz_info in quiz_data_list:
            items = [
                {"name": quiz_info["correct_answer"], "image_url": image_urls[url_index]},
                {"name": quiz_info["wrong_names"][0], "image_url": image_urls[url_index + 1]},
                {"name": quiz_info["wrong_names"][1], "image_url": image_urls[url_index + 2]},
            ]
            random.shuffle(items)
            url_index += 3
            FirstGameQuiz.objects.create(
                user=user,
                prompt_text=quiz_info["prompt_text"],
                items=items,
                correct_answer=quiz_info["correct_answer"],
                is_ready=True
            )
        print(f"User {user_id}를 위한 퀴즈 3개 백그라운드 생성 완료")
    except Exception as e:
        print(f"Quiz generation task error for user {user_id}: {e}")

class StartGameSessionView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = GameSessionCreateSerializer(data=request.data)
        if serializer.is_valid():
            game_session = serializer.save()
            return Response({'session_id': game_session.session_id}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LogGameInteractionView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = GameInteractionLogSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({'message': 'Log saved successfully.'}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class BaseEndGameSessionView(APIView):
    serializer_class = None
    score_field_name = ''

    def post(self, request, *args, **kwargs):
        if not self.serializer_class or not self.score_field_name:
            raise NotImplementedError("serializer_class and score_field_name must be set")

        serializer = self.serializer_class(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        session_id = serializer.validated_data['session_id']
        score = serializer.validated_data[self.score_field_name]
        assistance_level = serializer.validated_data.get('assistance_level', None)

        try:
            with transaction.atomic():
                game_session = GameSession.objects.get(pk=session_id)
                if game_session.session_end_time is not None:
                    return Response({"message": "Session has already ended."}, status=status.HTTP_400_BAD_REQUEST)

                game_session.session_end_time = timezone.now()
                game_session.assistance_level = assistance_level
                game_session.save(update_fields=['session_end_time', 'assistance_level'])

                if score > 0:
                    user = User.objects.get(pk=game_session.user_id)
                    user.point = (user.point or 0) + score
                    user.save(update_fields=['point'])

            return Response({"message": f"Session {session_id} ended and points updated successfully."}, status=status.HTTP_200_OK)
        except GameSession.DoesNotExist:
            return Response({"error": "Game session not found."}, status=status.HTTP_404_NOT_FOUND)
        except User.DoesNotExist:
            return Response({"error": f"User not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": "An internal server error occurred."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class EndFirstGameSessionView(BaseEndGameSessionView):
    serializer_class = FirstGameEndSessionSerializer
    score_field_name = 'correct_answers'

    def post(self, request, *args, **kwargs):
        quiz_ids = request.data.get('quiz_ids', [])
        if quiz_ids:
            try:
                session = GameSession.objects.get(pk=request.data.get('session_id'))
                user_id = session.user_id
                FirstGameQuiz.objects.filter(quiz_id__in=quiz_ids, user_id=user_id).delete()
            except GameSession.DoesNotExist:
                # 세션을 못찾아도 일단 다음 로직은 실행되도록 함
                pass
        return super().post(request, *args, **kwargs)

class EndSecondGameSessionView(BaseEndGameSessionView):
    serializer_class = SecondGameEndSessionSerializer
    score_field_name = 'completed_count'

class EndThirdGameSessionView(BaseEndGameSessionView):
    serializer_class = ThirdGameEndSessionSerializer
    score_field_name = 'successful_throws'

class EndFourthGameSessionView(BaseEndGameSessionView):
    serializer_class = FourthGameEndSessionSerializer
    score_field_name = 'choices_made'
    def post(self, request, *args, **kwargs):
        request.data['choices_made'] = 0 
        return super().post(request, *args, **kwargs)

class TriggerQuizGenerationView(APIView):
    """AI 퀴즈 생성을 백그라운드에서 시작시키는 API"""
    def post(self, request, *args, **kwargs):
        serializer = QuizGenerationRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        user_id = serializer.validated_data['user_id']
        thread = threading.Thread(target=create_quiz_set, args=(user_id,))
        thread.start()
        return Response({"message": "Quiz generation started in the background."}, status=status.HTTP_202_ACCEPTED)

class GetReadyQuizzesView(APIView):
    """미리 생성된 퀴즈 3개를 DB에서 가져와 반환하는 API (삭제 로직 제거)"""
    def post(self, request, *args, **kwargs):
        serializer = QuizGenerationRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        user_id = serializer.validated_data['user_id']
        
        quizzes_to_play = FirstGameQuiz.objects.filter(user_id=user_id, is_ready=True).order_by('created_at')[:3]

        if quizzes_to_play.count() < 3:
            return Response({"error": "Quizzes are not ready yet. Please try again in a moment."}, status=status.HTTP_404_NOT_FOUND)
        
        # 퀴즈를 반환하기만 하고, 삭제하지 않음
        serializer = FirstGameQuizSerializer(quizzes_to_play, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
class DeleteLatestQuizzesView(APIView):
    """
    게임 종료 후, 가장 최근에 생성된 (사용하지 않은) 퀴즈 3개를 삭제하는 API
    """
    def post(self, request, *args, **kwargs):
        serializer = QuizGenerationRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        user_id = serializer.validated_data['user_id']

        try:
            # --- 핵심 수정: 슬라이싱된 쿼리셋을 삭제하는 올바른 방법 ---
            # 1. 삭제할 퀴즈들의 ID 목록을 먼저 가져옴
            latest_quizzes_ids = list(FirstGameQuiz.objects.filter(user_id=user_id).order_by('-created_at')[:3].values_list('quiz_id', flat=True))
            
            # 2. ID 목록을 사용하여 해당 퀴즈들을 삭제
            if latest_quizzes_ids:
                FirstGameQuiz.objects.filter(quiz_id__in=latest_quizzes_ids).delete()

            return Response({"message": "Cleaned up latest quizzes successfully."}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GetOrWaiteQuizzesView(APIView):
    """
    미리 생성된 퀴즈가 있으면 있다고 신호를 주고, 없으면 대기 신호를 주는 API
    """
    def post(self, request, *args, **kwargs):
        serializer = QuizGenerationRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        user_id = serializer.validated_data['user_id']
        
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        # 1. DB에서 준비된 퀴즈가 있는지 확인
        quizzes_to_play = FirstGameQuiz.objects.filter(user=user, is_ready=True).order_by('created_at')[:3]

        if quizzes_to_play.count() >= 3:
            # 퀴즈가 3개 이상 있으면, 퀴즈와 함께 'ready' 신호 반환
            serializer = FirstGameQuizSerializer(quizzes_to_play, many=True)
            return Response({"status": "ready", "quizzes": serializer.data}, status=status.HTTP_200_OK)
        else:
            # 퀴즈가 3개 미만이면, 'waiting' 신호만 반환
            return Response({"status": "waiting", "message": "퀴즈가 아직 준비되지 않았습니다. 잠시 후 다시 시도해주세요."}, status=status.HTTP_200_OK)
