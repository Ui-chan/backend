from django.core.management.base import BaseCommand
import random
import time
import json
import re
import traceback
import uuid
import os
import google.auth                 # ⇐ 이 줄을 추가하세요.
import google.auth.transport.requests # ⇐ 이 줄을 추가하세요.
import boto3
import google.generativeai as genai
import requests
from dotenv import load_dotenv
import base64 # ⇐ 이 줄을 추가하세요.
# --- 기본 설정 ---
load_dotenv()
try:
    gemini_api_key = os.environ.get("GEMINI_API_KEY")
    if not gemini_api_key:
        raise ValueError("GEMINI_API_KEY가 설정되지 않았습니다.")
    genai.configure(api_key=gemini_api_key)
    text_model = genai.GenerativeModel('gemini-1.5-flash')
except Exception as e:
    print(f"Gemini API 설정 오류: {e}")
    text_model = None

# --- S3 및 템플릿 정보 ---
S3_BUCKET_NAME = os.environ.get('AWS_STORAGE_BUCKET_NAME', 'iccas-quiz')
S3_REGION = os.environ.get('AWS_S3_REGION_NAME', 'ap-northeast-2')

QUIZ_TEMPLATES = [
    {
        "id": "swing_turn",
        "prompts": {
            "situation": {
                "positive": "A playground with one empty swing. The first character and the second character stand nearby, looking at the swing with EXCITED faces.",
                "negative": "sitting on the swing, only one character"
            },
            "correct": {
                "positive": "A happy scene. The first character is on the swing, SMILING. The second character is behind, pushing the swing and also SMILING.",
                "negative": "sad, angry, fighting, only one character"
            },
            "incorrect": {
                # ▼▼▼ 여기가 다시 수정된 부분입니다 ▼▼▼
                "positive": "The main subject of the image is a single playground swing. In the foreground, standing directly IN FRONT OF the swing, are the first character and the second character. They are facing each other, arguing about the swing. Both characters have VERY ANGRY expressions with furrowed brows.",
                # ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲
                "negative": "smiling, happy, playing, touching the swing, sitting on the swing, calm"
            }
        }
    },
    {
        "id": "blocks_knocked_over",
        "prompts": {
            "situation": {
                "positive": "A tall block tower has fallen over. The second character is on the floor CRYING with big tears. The first character, who knocked it over, looks SHOCKED with a wide-open mouth.",
                "negative": "smiling, happy, laughing, only one character"
            },
            "correct": {
                "positive": "The first character has a SORRY expression and is helping the second character rebuild the block tower. The second character is now SMILING.",
                "negative": "angry, fighting, arguing, only one character"
            },
            "incorrect": {
                # ▼▼▼ 여기가 최종 수정된 부분입니다 ▼▼▼
                "positive": "An emotionally divided scene. CRITICAL: The two characters MUST have OPPOSITE emotions. The setting is a floor with fallen blocks. The second character ('the victim') is in the foreground, sitting next to the blocks and CRYING with big tears. The first character ('the offender') is in the background, actively running away from the victim, and has a mischievous SMILING face. Do not show empathy.",
                # ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲
                "negative": "helping, happy victim, sad offender, crying offender, both characters crying, same emotion on both characters"
            }
        }
    },
]

def _validate_image_with_prompt(prompt, image_data_bytes):
    try:
        validator_prompt = f"You are a precise image QA expert. Does the given IMAGE accurately depict ALL key elements from the given TEXT PROMPT? TEXT PROMPT: \"{prompt}\". Respond ONLY with a valid JSON object: {{\"is_match\": boolean, \"reason\": \"brief explanation in Korean\"}}"
        image_part = {"mime_type": "image/png", "data": image_data_bytes}
        response = text_model.generate_content([validator_prompt, image_part], request_options={'timeout': 60})
        raw_text = response.text
        match = re.search(r'\{[\s\S]*\}', raw_text)
        if not match: return False, f"유효하지 않은 검증 응답: {raw_text}"
        result_json = json.loads(match.group(0))
        return result_json.get("is_match", False), result_json.get("reason", "No reason provided.")
    except Exception as e:
        return False, f"검증 중 에러 발생: {e}"

def _generate_and_upload_one_image(prompt, s3_key_prefix, negative_prompt=None):
    try:
        credentials, project_id = google.auth.default(scopes=['https://www.googleapis.com/auth/cloud-platform'])
        auth_req = google.auth.transport.requests.Request()
        credentials.refresh(auth_req)
        location = "us-central1"
        api_url = f"https://{location}-aiplatform.googleapis.com/v1/projects/{project_id}/locations/{location}/publishers/google/models/imagegeneration@006:predict"
        payload = {"instances": [{"prompt": prompt}], "parameters": {"sampleCount": 1, "aspectRatio": "1:1"}}
        if negative_prompt:
            payload["parameters"]["negativePrompt"] = negative_prompt
        headers = {"Authorization": f"Bearer {credentials.token}", "Content-Type": "application/json; charset=utf-8"}
        img_response = requests.post(api_url, json=payload, headers=headers, timeout=120)
        img_response.raise_for_status()
        result = img_response.json()
        if "predictions" in result and result.get("predictions"):
            base64_image = result["predictions"][0]["bytesBase64Encoded"]
            image_data_bytes = base64.b64decode(base64_image)
            is_valid, reason = _validate_image_with_prompt(prompt, image_data_bytes)
            if is_valid:
                s3_client = boto3.client('s3', aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'), aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'), region_name=S3_REGION)
                image_filename = f"{s3_key_prefix}{uuid.uuid4()}.png"
                s3_client.put_object(Bucket=S3_BUCKET_NAME, Key=image_filename, Body=image_data_bytes, ContentType='image/png')
                return f"https://{S3_BUCKET_NAME}.s3.{S3_REGION}.amazonaws.com/{image_filename}", reason
            else:
                return None, reason
        else:
            return None, f"API 응답에 prediction 없음: {result}"
    except Exception as e:
        return None, f"이미지 생성 중 에러 발생: {e}"

CHARACTER_PAIRS = [
    ["a cute fluffy bunny", "a kind brown bear"],
    ["a playful puppy with floppy ears", "a tiny kitten with big blue eyes"],
    ["a cheerful ladybug with big green eyes", "a curious little squirrel"],
    ["a sleepy panda cub", "a brave little lion cub"],
    ["a friendly giraffe with long eyelashes", "a small, happy elephant"],
]


# --- Django 관리 명령어 클래스 ---
class Command(BaseCommand):
    help = 'Generates and uploads validated quiz image assets to S3.'

    def add_arguments(self, parser):
        """명령어 실행 시 받을 인자(argument)를 정의합니다."""
        parser.add_argument('template_id', type=str, help='The ID of the quiz template (e.g., swing_turn).')
        parser.add_argument(
            'category', 
            type=str, 
            help="The category to generate images for ('situation', 'correct', 'incorrect', or 'all')."
        )
        parser.add_argument('count', type=int, help='The number of images to generate per category.')

    def _run_generation_for_category(self, category_name, prompts_data, count, template_id):
        """특정 카테고리에 대한 이미지 생성 루프를 실행하는 헬퍼 메서드"""
        self.stdout.write(f"\n--- Generating {count} images for category: {category_name} ---")
        s3_prefix = f"social_quiz/{template_id}/{category_name}/"
        successful_uploads = 0
        total_attempts = 0

        while successful_uploads < count:
            total_attempts += 1
            self.stdout.write(f"  Attempting to create image #{successful_uploads + 1} (Total tries: {total_attempts})...")
            
            # 미리 정의된 리스트에서 캐릭터를 무작위로 선택
            char1_desc, char2_desc = random.choice(CHARACTER_PAIRS)
            self.stdout.write(f"    -> Selected Characters: {char1_desc}, {char2_desc}")

            art_style = "Style: hyper-expressive and cute cartoon for toddlers, high-quality vector art, soft and friendly colors, simple background."
            character_definition = f"The first character is {char1_desc}. The second character is {char2_desc}."
            
            positive_prompt = f"{character_definition} {prompts_data['positive']} {art_style}"
            negative_prompt = prompts_data.get('negative')
            
            # 이미지 생성, 검증, 업로드 시도
            image_url, reason = _generate_and_upload_one_image(positive_prompt, s3_prefix, negative_prompt)
            
            if image_url:
                successful_uploads += 1
                self.stdout.write(self.style.SUCCESS(f"    -> Success! Image #{successful_uploads} saved to S3."))
            else:
                self.stdout.write(self.style.WARNING(f"    -> Failed. Reason: {reason}. Retrying..."))
        
        self.stdout.write(self.style.SUCCESS(f"--- Finished for category: {category_name} ---"))

    def handle(self, *args, **options):
        """명령어가 실행될 때 호출되는 메인 메서드"""
        template_id = options['template_id']
        category_to_generate = options['category']
        count = options['count']

        if not text_model:
            self.stderr.write(self.style.ERROR("Gemini API not configured."))
            return

        self.stdout.write(self.style.SUCCESS(f"Starting asset generation for template '{template_id}'..."))
        template = next((t for t in QUIZ_TEMPLATES if t['id'] == template_id), None)
        if not template:
            self.stderr.write(self.style.ERROR(f"Template '{template_id}' not found."))
            return

        # 'all' 인 경우, 모든 카테고리에 대해 생성
        if category_to_generate.lower() == 'all':
            for category, prompts_data in template['prompts'].items():
                self._run_generation_for_category(category, prompts_data, count, template_id)
        # 특정 카테고리가 지정된 경우
        else:
            prompts_data = template['prompts'].get(category_to_generate)
            if prompts_data:
                self._run_generation_for_category(category_to_generate, prompts_data, count, template_id)
            else:
                self.stderr.write(self.style.ERROR(f"Category '{category_to_generate}' not found in template '{template_id}'. "
                                                    f"Available categories are: {list(template['prompts'].keys())} or 'all'."))
                return

        self.stdout.write(self.style.SUCCESS("\nAll requested tasks completed!"))