from rest_framework import serializers
from .models import ChecklistResult

class ChecklistResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChecklistResult
        fields = '__all__'
        read_only_fields = ['result_id', 'created_at']

class HistoryRequestSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()

class DailyDataPointSerializer(serializers.Serializer):
    date = serializers.DateField()
    value = serializers.FloatField()

class AssistanceDataSerializer(serializers.Serializer):
    NONE = serializers.FloatField(default=0)
    VERBAL = serializers.FloatField(default=0)
    PHYSICAL = serializers.FloatField(default=0)

class Game1ProcessedStatsSerializer(serializers.Serializer):
    """'저기 봐!' 게임의 가공된 통계 (수정)"""
    daily_success_rate_trend = DailyDataPointSerializer(many=True)
    daily_response_time_trend = DailyDataPointSerializer(many=True)
    today_attempts = serializers.IntegerField()
    today_success_rate = serializers.FloatField()
    overall_avg_success_rate = serializers.FloatField()
    success_rate_by_assistance = AssistanceDataSerializer()
    overall_avg_response_time = serializers.FloatField()
    # '오늘 플레이 시간' 필드 추가
    today_play_duration_seconds = serializers.FloatField()

class Game2ProcessedStatsSerializer(serializers.Serializer):
    daily_response_time_trend = DailyDataPointSerializer(many=True)
    overall_avg_response_time = serializers.FloatField()
    today_play_count = serializers.IntegerField()
    today_play_duration_seconds = serializers.FloatField()
    avg_daily_play_time_seconds = serializers.FloatField()
    play_time_by_assistance = AssistanceDataSerializer()

class Game3ProcessedStatsSerializer(serializers.Serializer):
    """'공 주고받기' 게임의 가공된 통계 (수정)"""
    daily_success_rate_trend = DailyDataPointSerializer(many=True)
    daily_avg_power_trend = DailyDataPointSerializer(many=True)
    today_attempts = serializers.IntegerField()
    today_success_rate = serializers.FloatField()
    overall_avg_success_rate = serializers.FloatField()
    avg_power_by_assistance = AssistanceDataSerializer()
    success_rate_by_assistance = AssistanceDataSerializer()
    # '오늘 플레이 시간' 필드 추가
    today_play_duration_seconds = serializers.FloatField()

class ProcessedStatsSerializer(serializers.Serializer):
    game1 = Game1ProcessedStatsSerializer()
    game2 = Game2ProcessedStatsSerializer()
    game3 = Game3ProcessedStatsSerializer()

class StatsRequestSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()