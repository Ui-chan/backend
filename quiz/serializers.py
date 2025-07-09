from rest_framework import serializers
from .models import Quiz

class QuizSerializer(serializers.ModelSerializer):
    """
    퀴즈 데이터를 보여주기 위한 Serializer
    """
    class Meta:
        model = Quiz
        fields = '__all__' # 모델의 모든 필드를 포함

class QuizCreateSerializer(serializers.Serializer):
    """
    퀴즈 생성을 위해 user_id를 입력받기 위한 Serializer
    """
    user_id = serializers.IntegerField()

class QuizAnswerSerializer(serializers.Serializer):
    """
    사용자의 답변(selected)을 입력받기 위한 Serializer
    """
    selected = serializers.CharField(max_length=255)