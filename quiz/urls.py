from django.urls import path
from .views import *

urlpatterns = [
    path('', QuizListView.as_view()),
    
    path('firstgame/create/', QuizCreateView.as_view()),
    path('firstgame/save/', FirstGameResultSaveView.as_view()),
    
    path('secondgame/create/', SecondGameCreateView.as_view()),
    path('secondgame/save/', SecondGameResultSaveView.as_view()),

    path('cardgame/create/', CardGameCreateView.as_view()),
    path('cardgame/save/', ThirdGameResultSaveView.as_view()),
]