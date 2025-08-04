from django.urls import path
# 수정된 View들을 import 합니다.
from .views import *

app_name = 'games'

urlpatterns = [
    # 공용 API 경로
    path('session/start/', StartGameSessionView.as_view()),
    path('interaction/log/', LogGameInteractionView.as_view()),

    # 각 게임별 종료 API 경로
    path('first-game/session/end/', EndFirstGameSessionView.as_view()),
    path('second-game/session/end/', EndSecondGameSessionView.as_view()),
    path('third-game/session/end/', EndThirdGameSessionView.as_view()),
    path('fourth-game/session/end/', EndFourthGameSessionView.as_view()), # 새로 추가
]