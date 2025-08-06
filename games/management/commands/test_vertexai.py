# games/management/commands/test_vertexai.py

from django.core.management.base import BaseCommand
from django.conf import settings
import vertexai
from vertexai.preview.vision_models import ImageGenerationModel
import uuid
import boto3
from botocore.exceptions import NoCredentialsError

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
    except Exception as e:
        print(f"S3 upload failed: {e}")
        return None

class Command(BaseCommand):
    help = 'Tests Vertex AI image generation with a simple prompt.'

    def handle(self, *args, **kwargs):
        self.stdout.write("Vertex AI 이미지 생성 테스트를 시작합니다...")
        
        prompt = "A smiling cartoon apple"
        
        try:
            vertexai.init(project=settings.GCP_PROJECT_ID, location=settings.GCP_LOCATION)
            model = ImageGenerationModel.from_pretrained("imagegeneration@005")
            
            detailed_prompt = f"A simple, cute cartoon illustration of a {prompt}, on a clean white background"
            
            self.stdout.write(f"요청 프롬프트: '{detailed_prompt}'")
            
            images = model.generate_images(
                prompt=detailed_prompt,
                number_of_images=1,
                negative_prompt="text, words, realistic, photo, scary, complex"
            )
            
            self.stdout.write("Vertex AI로부터 이미지를 성공적으로 받았습니다. S3에 업로드를 시도합니다...")
            
            image_bytes = images[0]._image_bytes
            bucket_name = settings.AWS_STORAGE_BUCKET_NAME
            object_name = f"test-images/{prompt.replace(' ', '_')}_{uuid.uuid4().hex}.png"
            
            image_url = upload_to_s3(image_bytes, bucket_name, object_name)

            if image_url:
                self.stdout.write(self.style.SUCCESS(f"테스트 성공! 이미지 URL: {image_url}"))
            else:
                self.stdout.write(self.style.ERROR("S3 업로드에 실패했습니다."))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Vertex AI 이미지 생성 중 에러가 발생했습니다: {e}"))