import os
from celery import Celery

# Django의 settings 모듈을 Celery의 기본 설정으로 사용하도록 설정합니다.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Zerodose.settings')

app = Celery('Zerodose')

# Django settings.py에 정의된 'CELERY_'로 시작하는 모든 설정을 로드합니다.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Django 앱 디렉토리 내의 모든 tasks.py 파일을 자동으로 찾습니다.
app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')