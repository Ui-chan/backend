from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from django.db import transaction
from .models import GameSession
# 간결하게 수정한 Serializer들을 import 합니다.
from .serializers import *
from users.models import User

# --- 공용 View ---

class StartGameSessionView(APIView):
    """
    모든 게임의 세션 시작을 처리하는 공용 View
    """
    def post(self, request, *args, **kwargs):
        serializer = GameSessionCreateSerializer(data=request.data)
        if serializer.is_valid():
            game_session = serializer.save()
            return Response({
                "message": f"Game session for game_id {game_session.game_id} started successfully.",
                "session_id": game_session.session_id
            }, status=status.HTTP_201_CREATED) # HTTP_2_CREATED -> HTTP_201_CREATED 로 수정
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LogGameInteractionView(APIView):
    """
    모든 게임의 상호작용 기록을 처리하는 공용 View
    """
    def post(self, request, *args, **kwargs):
        serializer = GameInteractionLogSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Interaction logged successfully."}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# --- 게임별 종료 View ---
# 공통 로직을 담은 Base View를 만들고, 각 게임 View가 이를 상속받아 사용합니다.

class BaseEndGameSessionView(APIView):
    """
    세션 종료와 포인트 업데이트의 공통 로직을 담은 기본 View
    """
    serializer_class = None  # 각 게임별 Serializer를 지정
    score_field_name = ''    # 각 게임별 포인트 필드명을 지정

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

            return Response({
                "message": f"Session {session_id} ended and points updated successfully."
            }, status=status.HTTP_200_OK)
        except GameSession.DoesNotExist:
            return Response({"error": "Game session not found."}, status=status.HTTP_404_NOT_FOUND)
        except User.DoesNotExist:
            return Response({"error": f"User not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": "An internal server error occurred."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# 각 게임별 View는 BaseEndGameSessionView를 상속받아 필요한 부분만 정의
class EndFirstGameSessionView(BaseEndGameSessionView):
    serializer_class = FirstGameEndSessionSerializer
    score_field_name = 'correct_answers'

class EndSecondGameSessionView(BaseEndGameSessionView):
    serializer_class = SecondGameEndSessionSerializer
    score_field_name = 'completed_count'

class EndThirdGameSessionView(BaseEndGameSessionView):
    serializer_class = ThirdGameEndSessionSerializer
    score_field_name = 'successful_throws'

class EndFourthGameSessionView(BaseEndGameSessionView):
    serializer_class = FourthGameEndSessionSerializer
    score_field_name = 'choices_made' # 포인트 지급 변수

    def post(self, request, *args, **kwargs):
        # 포인트 지급 로직을 비활성화 하기 위해 score를 0으로 고정
        request.data['choices_made'] = 0 
        return super().post(request, *args, **kwargs)