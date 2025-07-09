from django.http import JsonResponse
from .models import Quiz
from .serializers import QuizSerializer

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import google.auth
import google.auth.transport.requests

import os
import json
import requests
import random
import boto3
import base64
import uuid
import traceback
from dotenv import load_dotenv

import concurrent.futures
from django import db

load_dotenv()

# --- Gemini 및 Vertex AI 설정 ---
try:
    gemini_api_key = os.environ.get("GEMINI_API_KEY")
    if not gemini_api_key: raise ValueError("GEMINI_API_KEY가 설정되지 않았습니다.")
    genai.configure(api_key=gemini_api_key)
    text_model = genai.GenerativeModel('gemini-1.5-flash')
except Exception as e:
    print(f"Gemini API 설정 오류: {e}")
    text_model = None

# --- 상수 정의 ---
S3_BUCKET_NAME = 'iccas-quiz'
S3_REGION = 'ap-northeast-2'
VERTEX_AI_LOCATION = 'us-central1'
VERTEX_AI_MODEL = 'imagegeneration@006'

def create_new_quiz_data(user_id):
    """퀴즈 생성의 모든 과정을 담당하는 핵심 로직 (프롬프트 검열 포함)"""
    if not text_model:
        raise Exception("Gemini API가 설정되지 않았습니다.")

    image_prompt = None
    
    # 프롬프트 생성 및 검열을 위한 루프 (최대 3번 재시도)
    for attempt in range(3):
        print(f"--- [INFO] Quiz generation attempt {attempt + 1}/3 for user_id: {user_id} ---")
        emotion_map = { "Happiness": "기쁨", "Sadness": "슬픔", "Anger": "화남", "Surprise": "놀람" }
        chosen_emotion_en = random.choice(list(emotion_map.keys()))
        chosen_emotion_ko = emotion_map[chosen_emotion_en]
        
        story_prompt_templates = {
            "Happiness": "The story must be about **at least two cute animal characters** and describe them having **enormous, joyful smiles**.",
            "Sadness": "The story must be about **at least two cute animal characters** and describe at least one of them **visibly crying, with large tears**.",
            "Anger": "The story must be about **at least two cute animal characters** and describe one character's **face turning bright red with anger**.",
            "Surprise": "The story must be about **at least two cute animal characters** and describe **both** of their **mouths forming a perfect 'O' shape** in astonishment when they see the key object."
        }

        # 2. Gemini 프롬프트 최종 생성 - "두 마리 이상의 동물" 조건을 명확히 전달
        prompt_text = f"""
        You are a creative storyteller for a children's therapeutic app.
        Your task is to create a JSON object for a story about the emotion: **{chosen_emotion_en}**.

        **Requirement 1: The story MUST feature exactly THREE cute animal characters.**
        **Requirement 2: Do NOT give the characters proper names.** Describe them by their species or appearance (e.g., 'a fluffy rabbit', 'a tall giraffe', 'a sleepy cat').
        **Requirement 3: {story_prompt_templates.get(chosen_emotion_en, '')}**

        The JSON object must contain:
        1. "story_text": A story about three cute animal characters.
        2. "answer_en": This must be exactly "{chosen_emotion_en}".
        3. "characters": A list of descriptions for all THREE characters in the story.
        4. "key_object": A key object from the story.
        5. "answer_ko": This must be exactly "{chosen_emotion_ko}".
        6. "options_ko": A list of 4 Korean emotion words, including "{chosen_emotion_ko}".
        """
        

        response = text_model.generate_content([{"role": "user", "parts": [prompt_text]}])
        raw_text = response.text.strip()
        try:
            json_string = raw_text.strip('```json').strip()
            quiz_data = json.loads(json_string)
            if isinstance(quiz_data, list): quiz_data = quiz_data[0]
            if not isinstance(quiz_data, dict): raise Exception("유효한 JSON 객체가 아님")
        except (IndexError, json.JSONDecodeError):
            raise Exception(f"Gemini 응답 파싱 실패: {raw_text}")

        story_text = quiz_data.get('story_text')
        answer_en = quiz_data.get('answer_en')
        characters = quiz_data.get('characters')
        key_object = quiz_data.get('key_object')
        options_ko = quiz_data.get('options_ko')
        answer_ko = quiz_data.get('answer_ko')
        if not all([story_text, answer_en, characters, key_object, options_ko, answer_ko]):
            raise Exception(f"유효한 퀴즈 데이터를 받지 못했습니다: {quiz_data}")

        characters = quiz_data.get('characters')
        if not characters or len(characters) < 3:
            raise Exception(f"Gemini가 3명의 캐릭터를 생성하지 않았습니다: {characters}")

        char1, char2, char3 = characters[0], characters[1], characters[2]
        
        # 이미지 프롬프트 생성 (3마리 캐릭터를 모두 포함하도록 수정)
        image_prompt_templates = {
            "happiness": (
                f"A hyper-expressive cartoon of {char1}, {char2}, and {char3}. "
                f"The most important feature is their enormous, joyful smiles that stretch from ear to ear. "
                f"They are all celebrating together around {key_object}. Style: high-quality vector art for toddlers."
            ),
            "sadness": (
                f"A hyper-expressive cartoon of {char1}, {char2}, and {char3}. "
                f"The most important feature is that {char1} is visibly crying, with huge, comical, streaming tears. "
                f"Nearby, {char2} and {char3} have matching sad, empathetic expressions, looking at a broken {key_object}. "
                f"Style: high-quality vector art for toddlers."
            ),
            "anger": (
                f"A hyper-expressive cartoon of {char1}. "
                f"Its entire face is bright red with anger, and comical puffs of steam are coming out of its ears. "
                f"Nearby, {char2} and {char3} look on with worried expressions. "
                f"Style: high-quality vector art for toddlers."
            ),
            "surprise": (
                f"A hyper-expressive cartoon of {char1}, {char2}, and {char3}. "
                f"The absolute most important feature is that all three characters' mouths are frozen wide open in a perfect 'O' shape of astonishment. "
                f"They are all looking at {key_object}. Style: high-quality vector art for toddlers."
            )
        }
        temp_image_prompt = image_prompt_templates.get(answer_en.lower(), f"Three cute animal characters expressing '{answer_en}'.")

        # 프롬프트 검열
        forbidden_keywords = ['child', 'children', 'kid', 'kids', 'baby', 'babies', 'kill', 'fight', 'blood', 'violence']
        prompt_has_forbidden_word = any(word in temp_image_prompt.lower() for word in forbidden_keywords)

        if not prompt_has_forbidden_word:
            image_prompt = temp_image_prompt
            print("--- [INFO] Prompt validation passed. Proceeding to image generation. ---")
            break
        else:
            print(f"--- [WARNING] Forbidden keyword found in prompt. Retrying... ---\nPrompt: {temp_image_prompt}")
            
    if image_prompt is None:
        raise Exception("안전한 이미지 프롬프트를 생성하는 데 3번 실패했습니다.")

    # Vertex AI 인증 및 API 호출
    credentials, project_id = google.auth.default(scopes=['[https://www.googleapis.com/auth/cloud-platform](https://www.googleapis.com/auth/cloud-platform)'])
    auth_req = google.auth.transport.requests.Request()
    credentials.refresh(auth_req)
    if not project_id:
        raise Exception("Google Cloud Project ID를 찾을 수 없습니다.")
    
    location = "us-central1"
    api_url = f"https://{location}-aiplatform.googleapis.com/v1/projects/{project_id}/locations/{location}/publishers/google/models/imagegeneration@006:predict"

    payload = { "instances": [{"prompt": image_prompt}], "parameters": {"sampleCount": 1, "aspectRatio": "1:1"} }
    headers = { "Authorization": f"Bearer {credentials.token}", "Content-Type": "application/json; charset=utf-8" }
    
    print(f"--- [DEBUG] Sending to Vertex AI API ---\n{image_prompt}\n---------------------------------------")
    img_response = requests.post(api_url, json=payload, headers=headers, timeout=60)
    img_response.raise_for_status()
    result = img_response.json()
    if "predictions" not in result or not result.get("predictions"):
        raise ValueError("API가 이미지를 반환하지 않았습니다.")
    base64_image = result["predictions"][0]["bytesBase64Encoded"]

    # S3에 이미지 업로드
    s3_client = boto3.client('s3', aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'), aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'), region_name=S3_REGION)
    image_data = base64.b64decode(base64_image)
    image_filename = f"{user_id}/{uuid.uuid4()}.png"
    s3_client.put_object(Bucket=S3_BUCKET_NAME, Key=image_filename, Body=image_data, ContentType='image/png')
    image_url = f"https://{S3_BUCKET_NAME}.s3.{S3_REGION}.amazonaws.com/{image_filename}"
    
    # DB에 퀴즈 저장
    new_quiz = Quiz.objects.create(
        user_id=user_id,
        quiz_image=image_url,
        correct_answer=answer_ko,
        answer_list=options_ko,
        selected="",
        is_correct=""
    )
    print(f"--- [INFO] New Quiz created with ID: {new_quiz.quiz_id} for User ID: {user_id} ---")
    return new_quiz


class QuizListView(APIView):
    """ GET: 모든 퀴즈 목록을 보여줍니다. """
    def get(self, request):
        quizzes = Quiz.objects.all().order_by('-created_at')
        serializer = QuizSerializer(quizzes, many=True)
        return Response(serializer.data)


class QuizCreateView(APIView):
    def post(self, request):
        user_id = request.data.get('user_id')
        if user_id is None:
            return Response({'error': 'user_id가 필요합니다.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # 5명의 직원을 고용하고,
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                # user_id를 5번 전달하여 5개의 일감을 줍니다.
                results = executor.map(create_new_quiz_data, [user_id] * 5)
                new_quizzes = list(results)
            
            serializer = QuizSerializer(new_quizzes, many=True)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            print(traceback.format_exc())
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        finally:
            db.connections.close_all()