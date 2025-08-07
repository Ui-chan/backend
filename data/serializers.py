from rest_framework import serializers
from .models import ChecklistResult

# --- 데이터 단위를 위한 Serializer ---
class DailyDataPointSerializer(serializers.Serializer):
    date = serializers.DateField()
    value = serializers.FloatField()

class AssistanceDataSerializer(serializers.Serializer):
    NONE = serializers.FloatField(default=0)
    VERBAL = serializers.FloatField(default=0)
    PHYSICAL = serializers.FloatField(default=0)

# --- 각 게임별 상세 통계를 위한 Serializer ---
class Game1StatsSerializer(serializers.Serializer):
    today_attempts = serializers.IntegerField()
    today_success_rate = serializers.FloatField()
    today_play_duration_seconds = serializers.FloatField()
    
    overall_avg_success_rate = serializers.FloatField()
    overall_avg_response_time = serializers.FloatField()
    
    daily_success_rate_trend = DailyDataPointSerializer(many=True)
    daily_response_time_trend = DailyDataPointSerializer(many=True)
    
    success_rate_by_assistance = AssistanceDataSerializer()
    

class Game2StatsSerializer(serializers.Serializer):
    today_play_count = serializers.IntegerField()
    today_play_duration_seconds = serializers.FloatField()
    today_avg_response_time = serializers.FloatField()
    
    overall_avg_response_time = serializers.FloatField()
    avg_daily_play_time_seconds = serializers.FloatField()

    daily_response_time_trend = DailyDataPointSerializer(many=True)
    daily_play_time_trend = DailyDataPointSerializer(many=True)  # ✅ 날짜별 플레이 시간 추가

    play_time_by_assistance = AssistanceDataSerializer()



class Game3StatsSerializer(serializers.Serializer):
    today_attempts = serializers.IntegerField()
    today_success_rate = serializers.FloatField()
    today_play_duration_seconds = serializers.FloatField()
    
    overall_avg_success_rate = serializers.FloatField()
    # 전체 평균 throw power는 도움 수준별 데이터에서 대표로 사용 가능
    
    daily_success_rate_trend = DailyDataPointSerializer(many=True)
    daily_avg_power_trend = DailyDataPointSerializer(many=True)
    
    success_rate_by_assistance = AssistanceDataSerializer()
    avg_power_by_assistance = AssistanceDataSerializer()
    


# --- API 요청 및 최종 응답을 위한 Serializer ---
class ComprehensiveStatsSerializer(serializers.Serializer):
    """모든 데이터를 종합한 최종 통계 Serializer"""
    game1 = Game1StatsSerializer()
    game2 = Game2StatsSerializer()
    game3 = Game3StatsSerializer()

class StatsRequestSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()

# --- 체크리스트 관련 Serializer (기존 유지) ---
class ChecklistResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChecklistResult
        fields = '__all__'
        read_only_fields = ['result_id', 'created_at']

class HistoryRequestSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()

class DetectEmotionSerializer(serializers.Serializer):
    """DetectEmotionView를 위한 Serializer"""
    image = serializers.CharField()
    target_emotion = serializers.CharField()
    
    # --- MODIFICATION: response_time_ms 필드 추가 ---
    # 반응 시간(ms)을 입력받으며, 0 이상의 정수여야 합니다.
    response_time_ms = serializers.IntegerField(min_value=0)

class UserStatsWithAnalysisSerializer(serializers.Serializer):
    """사용자 통계와 AI 분석 결과를 함께 반환하기 위한 Serializer"""
    statistics = ComprehensiveStatsSerializer()
    game1_analysis = serializers.JSONField()
    game2_analysis = serializers.JSONField()
    game3_analysis = serializers.JSONField()