# backend

이 디렉토리는 Python 기반 Django 백엔드 서버입니다.  
아래 안내에 따라 개발 환경을 설정하고 서버를 실행할 수 있습니다.

---

## ⚙️ 1. 환경 설정

### 🟩 Conda 사용자

```bash
# Conda 환경 생성
conda env create -f environment.yml

# 환경 활성화
conda activate env

# 가상환경 생성
python -m venv venv

# 가상환경 활성화
source venv/bin/activate       # (Windows: venv\Scripts\activate)

# pip 패키지 설치
pip install -r requirements.txt

# Django 프로젝트 디렉토리로 이동 (manage.py가 있는 위치)
cd backend

# 개발 서버 실행
python manage.py runserver

http://localhost:8000
