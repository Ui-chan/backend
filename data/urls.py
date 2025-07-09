from django.urls import path
from .views import QuizResultCreateView

urlpatterns = [
    path('quiz_result/', QuizResultCreateView.as_view(), name='quiz_result_create'),
]
