from django.urls import path
from .views import *

urlpatterns = [
    path('checklist/save/', SaveChecklistResultView.as_view()),
    
    # 체크리스트 기록 조회 API: POST /api/data/checklist/history/
    path('checklist/history/', GetChecklistHistoryView.as_view()),

    path('user-stats/', ComprehensiveStatsView.as_view()),

    path('detect-emotion/', DetectEmotionView.as_view()),

]
