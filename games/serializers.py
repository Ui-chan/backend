from rest_framework import serializers
from .models import GameSession, GameInteractionLog, FirstGameQuiz

# 모든 게임이 공통으로 사용할 세션 및 로그 생성 Serializer
class GameSessionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = GameSession
        fields = ['user_id', 'game_id']

class GameInteractionLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = GameInteractionLog
        fields = '__all__'

# --- 각 게임별 종료 Serializer ---
# 게임마다 포인트 변수명이 다르므로 별도로 정의합니다.

class FirstGameEndSessionSerializer(serializers.Serializer):
    session_id = serializers.IntegerField()
    correct_answers = serializers.IntegerField()
    assistance_level = serializers.CharField(max_length=20)
    quiz_ids = serializers.ListField(
        child=serializers.IntegerField(), required=True # 이제 필수 항목입니다.
    )

class SecondGameEndSessionSerializer(serializers.Serializer):
    """두 번째 게임 세션 종료 Serializer"""
    session_id = serializers.IntegerField()
    completed_count = serializers.IntegerField(min_value=0)
    assistance_level = serializers.CharField(required=False, allow_blank=True, max_length=20)

class ThirdGameEndSessionSerializer(serializers.Serializer):
    """세 번째 게임 세션 종료 Serializer"""
    session_id = serializers.IntegerField()
    successful_throws = serializers.IntegerField(min_value=0)
    assistance_level = serializers.CharField(required=False, allow_blank=True, max_length=20)

# --- FourthGame Serializer (새로 추가) ---
class FourthGameEndSessionSerializer(serializers.Serializer):
    """네 번째 게임 세션 종료 Serializer"""
    session_id = serializers.IntegerField()
    choices_made = serializers.IntegerField(min_value=0)
    assistance_level = serializers.CharField(required=False, allow_blank=True, max_length=20)

class QuizItemSerializer(serializers.Serializer):
    """퀴즈에 포함될 각 보기 아이템의 형식을 정의합니다."""
    name = serializers.CharField()
    image_url = serializers.URLField()

class QuizGenerationRequestSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()

class FirstGameQuizSerializer(serializers.ModelSerializer):
    class Meta:
        model = FirstGameQuiz
        # --- 핵심 수정: quiz_id 필드 추가 ---
        fields = ['quiz_id', 'prompt_text', 'items', 'correct_answer']