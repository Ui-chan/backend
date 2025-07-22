from django.urls import path
from .views import *

urlpatterns = [
    # GET /api/quizzes/ - 모든 퀴즈 목록 조회
    path('quizzes/', QuizListView.as_view(), name='quiz-list'),
    
    # POST /api/quizzes/create/ - 새로운 퀴즈 생성
    path('firstgame/create/', QuizCreateView.as_view()),

    path('cardgame/create/', CardGameCreateView.as_view()),

    path('cardgame/save/', ThirdGameResultSaveView.as_view()),

    path('firstgame/save/', FirstGameResultSaveView.as_view()),
]