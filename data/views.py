from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from django.db.models import Avg, Count, Sum, F, Case, When
from django.db.models.functions import TruncDate
from collections import defaultdict

from games.models import GameSession, GameInteractionLog 
from .models import ChecklistResult
from .serializers import *

class SaveChecklistResultView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = ChecklistResultSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Checklist result saved successfully."}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class GetChecklistHistoryView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = HistoryRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        user_id = serializer.validated_data['user_id']
        history = ChecklistResult.objects.filter(user_id=user_id)
        history_serializer = ChecklistResultSerializer(history, many=True)
        return Response(history_serializer.data, status=status.HTTP_200_OK)

class ComprehensiveStatsView(APIView):
    """
    사용자의 '오늘', '도움 수준별', '전체/추이' 데이터를 모두 가공하여 반환하는 API
    """
    def post(self, request, *args, **kwargs):
        req_serializer = StatsRequestSerializer(data=request.data)
        if not req_serializer.is_valid():
            return Response(req_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        user_id = req_serializer.validated_data['user_id']
        today = timezone.now().date()

        sessions = GameSession.objects.filter(user_id=user_id)
        session_assistance_map = {s.session_id: s.assistance_level for s in sessions}
        logs = GameInteractionLog.objects.filter(session_id__in=sessions.values_list('session_id', flat=True))

        # --- 게임 1: 저기 봐! ---
        g1_sessions = sessions.filter(game_id=1)
        g1_logs = logs.filter(session_id__in=g1_sessions.values_list('session_id', flat=True))
        g1_today_logs = g1_logs.filter(timestamp__date=today)
        g1_today_sessions = g1_sessions.filter(session_start_time__date=today, session_end_time__isnull=False)
        g1_today_duration_agg = g1_today_sessions.aggregate(total=Sum(F('session_end_time') - F('session_start_time')))['total']
        
        daily_success_rate_trend_g1 = list(g1_logs.annotate(date=TruncDate('timestamp')).values('date').annotate(s=Count(Case(When(is_successful=True, then=1))), t=Count('log_id')).annotate(value=F('s')*100.0/F('t')).values('date', 'value').order_by('date'))
        daily_response_time_trend_g1 = list(g1_logs.filter(response_time_ms__isnull=False).annotate(date=TruncDate('timestamp')).values('date').annotate(value=Avg('response_time_ms')).values('date', 'value').order_by('date'))
        
        g1_assistance_success = defaultdict(int)
        g1_assistance_total = defaultdict(int)
        for log in g1_logs:
            level = session_assistance_map.get(log.session_id)
            if level:
                g1_assistance_total[level] += 1
                if log.is_successful: g1_assistance_success[level] += 1
        
        g1_stats = {
            'today_attempts': g1_today_logs.count(),
            'today_success_rate': (g1_today_logs.filter(is_successful=True).count() / g1_today_logs.count() * 100) if g1_today_logs.count() > 0 else 0,
            'today_play_duration_seconds': g1_today_duration_agg.total_seconds() if g1_today_duration_agg else 0,
            'overall_avg_success_rate': (g1_logs.filter(is_successful=True).count() / g1_logs.count() * 100) if g1_logs.count() > 0 else 0,
            'overall_avg_response_time': g1_logs.aggregate(avg=Avg('response_time_ms'))['avg'] or 0,
            'daily_success_rate_trend': daily_success_rate_trend_g1,
            'daily_response_time_trend': daily_response_time_trend_g1,
            'success_rate_by_assistance': { level: (g1_assistance_success[level] / g1_assistance_total[level] * 100) if g1_assistance_total[level] > 0 else 0 for level in ['NONE', 'VERBAL', 'PHYSICAL'] }
        }

        # --- 게임 2: 표정 짓기 ---
        g2_sessions = sessions.filter(game_id=2)
        g2_logs = logs.filter(session_id__in=g2_sessions.values_list('session_id', flat=True))
        daily_response_time_trend_g2 = list(g2_logs.filter(response_time_ms__isnull=False).annotate(date=TruncDate('timestamp')).values('date').annotate(value=Avg('response_time_ms')).values('date', 'value').order_by('date'))
        g2_today_sessions = g2_sessions.filter(session_start_time__date=today, session_end_time__isnull=False)
        today_play_duration_agg = g2_today_sessions.aggregate(total=Sum(F('session_end_time') - F('session_start_time')))['total']
        total_play_time_agg = g2_sessions.exclude(session_end_time__isnull=True).aggregate(total=Sum(F('session_end_time') - F('session_start_time')))['total']
        total_play_days = g2_sessions.annotate(date=TruncDate('session_start_time')).values('date').distinct().count()

        g2_stats = {
            'today_play_count': g2_today_sessions.count(),
            'today_play_duration_seconds': today_play_duration_agg.total_seconds() if today_play_duration_agg else 0,
            'today_avg_response_time': g2_logs.filter(timestamp__date=today).aggregate(avg=Avg('response_time_ms'))['avg'] or 0,
            'overall_avg_response_time': g2_logs.aggregate(avg=Avg('response_time_ms'))['avg'] or 0,
            'avg_daily_play_time_seconds': (total_play_time_agg.total_seconds() / total_play_days) if total_play_days > 0 else 0,
            'daily_response_time_trend': daily_response_time_trend_g2,
            'play_time_by_assistance': { level: (g2_sessions.filter(assistance_level=level, session_end_time__isnull=False).aggregate(total=Sum(F('session_end_time') - F('session_start_time')))['total'].total_seconds()) if g2_sessions.filter(assistance_level=level).exists() else 0 for level in ['NONE', 'VERBAL', 'PHYSICAL'] }
        }
        
        # --- 게임 3: 공 주고받기 ---
        g3_sessions = sessions.filter(game_id=3)
        g3_logs = logs.filter(session_id__in=g3_sessions.values_list('session_id', flat=True))
        g3_today_logs = g3_logs.filter(timestamp__date=today)
        g3_today_sessions = g3_sessions.filter(session_start_time__date=today, session_end_time__isnull=False)
        g3_today_duration_agg = g3_today_sessions.aggregate(total=Sum(F('session_end_time') - F('session_start_time')))['total']

        daily_g3_success_rate_trend = list(g3_logs.annotate(date=TruncDate('timestamp')).values('date').annotate(s=Count(Case(When(is_successful=True, then=1))), t=Count('log_id')).annotate(value=F('s')*100.0/F('t')).values('date', 'value').order_by('date'))
        
        daily_power_data, g3_assistance_power = defaultdict(lambda: {'total': 0, 'count': 0}), defaultdict(lambda: {'total': 0, 'count': 0})
        g3_assistance_success, g3_assistance_total = defaultdict(int), defaultdict(int)
        for log in g3_logs:
            power = log.interaction_data.get('throw_power')
            if power is not None:
                date = log.timestamp.date()
                daily_power_data[date]['total'] += power
                daily_power_data[date]['count'] += 1
            level = session_assistance_map.get(log.session_id)
            if level:
                g3_assistance_total[level] += 1
                if log.is_successful: g3_assistance_success[level] += 1
                if power is not None:
                    g3_assistance_power[level]['total'] += power
                    g3_assistance_power[level]['count'] += 1

        daily_avg_power_trend = [{'date': date, 'value': data['total'] / data['count']} for date, data in sorted(daily_power_data.items())]

        g3_stats = {
            'today_attempts': g3_today_logs.count(),
            'today_success_rate': (g3_today_logs.filter(is_successful=True).count() / g3_today_logs.count() * 100) if g3_today_logs.count() > 0 else 0,
            'today_play_duration_seconds': g3_today_duration_agg.total_seconds() if g3_today_duration_agg else 0,
            'overall_avg_success_rate': (g3_logs.filter(is_successful=True).count() / g3_logs.count() * 100) if g3_logs.count() > 0 else 0,
            'daily_success_rate_trend': daily_g3_success_rate_trend,
            'daily_avg_power_trend': daily_avg_power_trend,
            'success_rate_by_assistance': { level: (g3_assistance_success[level] / g3_assistance_total[level] * 100) if g3_assistance_total[level] > 0 else 0 for level in ['NONE', 'VERBAL', 'PHYSICAL'] },
            'avg_power_by_assistance': { level: (data['total'] / data['count']) if data['count'] > 0 else 0 for level, data in g3_assistance_power.items() }
        }
        
        processed_data = {'game1': g1_stats, 'game2': g2_stats, 'game3': g3_stats }
        
        serializer = ComprehensiveStatsSerializer(data=processed_data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data, status=status.HTTP_200_OK)