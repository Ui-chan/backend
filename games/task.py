import random
import uuid
import boto3
from botocore.exceptions import NoCredentialsError
from celery import shared_task
from django.conf import settings
import vertexai
from vertexai.preview.vision_models import ImageGenerationModel

from .models import FirstGameQuiz
from users.models import User

def upload_to_s3(image_bytes, bucket_name, object_name):
    """S3에 이미지 바이트를 업로드하고 URL을 반환하는 함수"""
    s3_client = boto3.client(
        's3',
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_S3_REGION_NAME
    )
    try:
        s3_client.put_object(Body=image_bytes, Bucket=bucket_name, Key=object_name, ContentType='image/png')
        url = f"https://{bucket_name}.s3.{settings.AWS_S3_REGION_NAME}.amazonaws.com/{object_name}"
        return url
    except NoCredentialsError:
        print("S3 credentials not available")
        return None
    except Exception as e:
        print(f"S3 upload failed: {e}")
        return None

def generate_image_with_vertex_ai(prompt: str) -> str:
    """Vertex AI Imagen을 호출하여 이미지를 생성하고 S3에 업로드 후 URL을 반환하는 함수"""
    try:
        vertexai.init(project=settings.GCP_PROJECT_ID, location=settings.GCP_LOCATION)
        model = ImageGenerationModel.from_pretrained("imagegeneration@005")
        
        # 프롬프트를 단순하고 직접적으로 유지
        detailed_prompt = f"A simple cartoon of a {prompt}, on a clean white background, for children's learning"
        
        images = model.generate_images(
            prompt=detailed_prompt,
            number_of_images=1,
            negative_prompt="text, words, realistic, photo, scary, complex, multiple objects"
        )
        
        image_bytes = images[0]._image_bytes
        bucket_name = settings.AWS_STORAGE_BUCKET_NAME
        object_name = f"quiz-images/{prompt.replace(' ', '_')}_{uuid.uuid4().hex}.png"
        
        image_url = upload_to_s3(image_bytes, bucket_name, object_name)
        return image_url
    except Exception as e:
        print(f"Vertex AI image generation failed for prompt '{prompt}': {e}")
        return None

@shared_task
def generate_quiz_set_for_user(user_id):
    """한 사용자를 위한 3개의 퀴즈 세트를 AI로 생성하여 DB에 저장하는 Celery Task"""
    try:
        user = User.objects.get(pk=user_id)

        # --- 영문 번역을 위한 딕셔너리 ---
        item_translation = {
            "사과": "apple", "자동차": "car", "오리": "duck", "바나나": "banana",
            "공": "ball", "집": "house", "강아지": "dog", "고양이": "cat"
        }
        color_translation = { "빨간": "red", "노란": "yellow", "파란": "blue", "갈색": "brown" }
        
        quiz_samples = [
            {"prompt": "🍎 빨간 사과는 어디 있지?", "correct": "사과", "color": "빨간", "wrong": ["자동차", "오리"]},
            {"prompt": "🍌 노란 바나나는 어디 있지?", "correct": "바나나", "color": "노란", "wrong": ["공", "집"]},
            {"prompt": "🚗 파란 자동차는 어디 있지?", "correct": "자동차", "color": "파란", "wrong": ["강아지", "고양이"]},
            {"prompt": "🐶 갈색 강아지는 어디 있지?", "correct": "강아지", "color": "갈색", "wrong": ["바나나", "사과"]},
        ]

        for _ in range(3):
            sample = random.choice(quiz_samples)
            
            correct_item_name = sample["correct"]
            wrong_items_names = sample["wrong"]
            
            # --- 색상과 사물을 영어로 조합하여 이미지 생성 프롬프트 만들기 ---
            correct_prompt = f"{color_translation[sample['color']]} {item_translation[correct_item_name]}"
            wrong_prompt_1 = item_translation[wrong_items_names[0]]
            wrong_prompt_2 = item_translation[wrong_items_names[1]]

            correct_item_url = generate_image_with_vertex_ai(correct_prompt)
            wrong_item_1_url = generate_image_with_vertex_ai(wrong_prompt_1)
            wrong_item_2_url = generate_image_with_vertex_ai(wrong_prompt_2)
            
            if not all([correct_item_url, wrong_item_1_url, wrong_item_2_url]):
                print(f"User {user_id}의 퀴즈 이미지 생성 중 하나 이상 실패")
                continue

            items_list = [
                {"name": correct_item_name, "image_url": correct_item_url},
                {"name": wrong_items_names[0], "image_url": wrong_item_1_url},
                {"name": wrong_items_names[1], "image_url": wrong_item_2_url},
            ]
            random.shuffle(items_list)

            FirstGameQuiz.objects.create(
                user=user,
                prompt_text=sample["prompt"],
                items=items_list,
                correct_answer=correct_item_name,
                is_ready=True
            )
        return f"User {user_id}를 위한 Vertex AI 퀴즈 3개 생성 완료"
    except User.DoesNotExist:
        return f"User {user_id}를 찾을 수 없음"