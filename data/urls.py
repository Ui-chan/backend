from django.urls import path
from .views import *

urlpatterns = [
    path('checklist/save/', SaveChecklistResultView.as_view()),
    
    # 체크리스트 기록 조회 API: POST /api/data/checklist/history/
    path('checklist/history/', GetChecklistHistoryView.as_view()),

    path('user-stats/', ComprehensiveStatsView.as_view()),

    path('detect-emotion/', DetectEmotionView.as_view()),

    path('ai-analysis/game1/', AnalyzeGame1StatsView.as_view()),
    path('ai-analysis/game2/', AnalyzeGame2StatsView.as_view()),
    path('ai-analysis/game3/', AnalyzeGame3StatsView.as_view()),

    path('rl/game3/difficulty/', Game3RLDifficultyView.as_view(), name='game3-rl-difficulty'),

]
