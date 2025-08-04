from rest_framework import serializers
from .models import GameSession, GameInteractionLog

# 모든 게임이 공통으로 사용할 세션 및 로그 생성 Serializer
class GameSessionCreateSerializer(serializers.ModelSerializer):
    """게임 세션 생성을 위한 공용 Serializer"""
    class Meta:
        model = GameSession
        fields = ['session_id', 'user_id', 'game_id', 'session_start_time']
        read_only_fields = ['session_id', 'session_start_time']

class GameInteractionLogSerializer(serializers.ModelSerializer):
    """게임 상호작용 기록을 위한 공용 Serializer"""
    class Meta:
        model = GameInteractionLog
        fields = ['log_id', 'session_id', 'is_successful', 'response_time_ms', 'interaction_data', 'timestamp']
        read_only_fields = ['log_id', 'timestamp']

# --- 각 게임별 종료 Serializer ---
# 게임마다 포인트 변수명이 다르므로 별도로 정의합니다.

class FirstGameEndSessionSerializer(serializers.Serializer):
    """첫 번째 게임 세션 종료 Serializer"""
    session_id = serializers.IntegerField()
    correct_answers = serializers.IntegerField(min_value=0)
    assistance_level = serializers.CharField(required=False, allow_blank=True, max_length=20)

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