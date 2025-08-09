# data/views.py

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from django.db.models import Avg, Count, Sum, F, Case, When, DurationField
from django.db.models.functions import TruncDate
from collections import defaultdict
from google.cloud import vision
import base64
from .serializers import *
import google.generativeai as genai
import os
import json
from dotenv import load_dotenv
from datetime import date, timedelta

from games.models import GameSession, GameInteractionLog 
from .models import ChecklistResult
from users.models import User  

from .agent import QLearningAgent
from .rl_utils import get_user_state, calculate_reward_and_next_state


class DateEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, date):
            return o.isoformat()
        return super().default(o)

# --- Stats Generation Functions ---

def _get_base_querysets(user_id):
    today = timezone.now().date()
    sessions = GameSession.objects.filter(user_id=user_id)
    if not sessions.exists():
        return None, None, None, today
    session_assistance_map = {s.session_id: s.assistance_level for s in sessions}
    logs = GameInteractionLog.objects.filter(session_id__in=sessions.values_list('session_id', flat=True))
    return sessions, logs, session_assistance_map, today

def _generate_game1_stats(user_id: int, sessions, logs, session_assistance_map, today) -> dict:
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
    return {
        'today_attempts': g1_today_logs.count(),
        'today_success_rate': (g1_today_logs.filter(is_successful=True).count() / g1_today_logs.count() * 100) if g1_today_logs.count() > 0 else 0,
        'today_play_duration_seconds': g1_today_duration_agg.total_seconds() if g1_today_duration_agg else 0,
        'overall_avg_success_rate': (g1_logs.filter(is_successful=True).count() / g1_logs.count() * 100) if g1_logs.count() > 0 else 0,
        'overall_avg_response_time': g1_logs.aggregate(avg=Avg('response_time_ms'))['avg'] or 0,
        'daily_success_rate_trend': daily_success_rate_trend_g1,
        'daily_response_time_trend': daily_response_time_trend_g1,
        'success_rate_by_assistance': { level: (g1_assistance_success[level] / g1_assistance_total[level] * 100) if g1_assistance_total[level] > 0 else 0 for level in ['NONE', 'VERBAL', 'PHYSICAL'] }
    }

def _generate_game2_stats(user_id: int, sessions, logs, session_assistance_map, today) -> dict:
    g2_sessions = sessions.filter(game_id=2)
    g2_logs = logs.filter(session_id__in=g2_sessions.values_list('session_id', flat=True))
    daily_response_time_trend_g2 = list(g2_logs.filter(response_time_ms__isnull=False).annotate(date=TruncDate('timestamp')).values('date').annotate(value=Avg('response_time_ms')).values('date', 'value').order_by('date'))
    g2_today_sessions = g2_sessions.filter(session_start_time__date=today, session_end_time__isnull=False)
    today_play_duration_agg = g2_today_sessions.aggregate(total=Sum(F('session_end_time') - F('session_start_time')))['total']
    total_play_time_agg = g2_sessions.exclude(session_end_time__isnull=True).aggregate(total=Sum(F('session_end_time') - F('session_start_time')))['total']
    total_play_days = g2_sessions.annotate(date=TruncDate('session_start_time')).values('date').distinct().count()
    daily_g2_play_time = (g2_sessions.exclude(session_end_time__isnull=True).annotate(date=TruncDate('session_start_time')).values('date').annotate(total_duration=Sum(F('session_end_time') - F('session_start_time'))))
    daily_play_time_trend_g2 = [{'date': entry['date'], 'value': entry['total_duration'].total_seconds() if entry['total_duration'] else 0} for entry in daily_g2_play_time]
    play_time_by_assistance = {}
    for level in ['NONE', 'VERBAL', 'PHYSICAL']:
        duration_agg = g2_sessions.filter(assistance_level=level, session_end_time__isnull=False).aggregate(total=Sum(F('session_end_time') - F('session_start_time'), output_field=DurationField()))['total']
        play_time_by_assistance[level] = duration_agg.total_seconds() if duration_agg else 0
    return {
        'today_play_count': g2_today_sessions.count(),
        'today_play_duration_seconds': today_play_duration_agg.total_seconds() if today_play_duration_agg else 0,
        'today_avg_response_time': g2_logs.filter(timestamp__date=today).aggregate(avg=Avg('response_time_ms'))['avg'] or 0,
        'overall_avg_response_time': g2_logs.aggregate(avg=Avg('response_time_ms'))['avg'] or 0,
        'avg_daily_play_time_seconds': (total_play_time_agg.total_seconds() / total_play_days) if total_play_days > 0 and total_play_time_agg else 0,
        'daily_response_time_trend': daily_response_time_trend_g2,
        'daily_play_time_trend': daily_play_time_trend_g2,
        'play_time_by_assistance': play_time_by_assistance
    }

def _generate_game3_stats(user_id: int, sessions, logs, session_assistance_map, today) -> dict:
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
    return {
        'today_attempts': g3_today_logs.count(),
        'today_success_rate': (g3_today_logs.filter(is_successful=True).count() / g3_today_logs.count() * 100) if g3_today_logs.count() > 0 else 0,
        'today_play_duration_seconds': g3_today_duration_agg.total_seconds() if g3_today_duration_agg else 0,
        'overall_avg_success_rate': (g3_logs.filter(is_successful=True).count() / g3_logs.count() * 100) if g3_logs.count() > 0 else 0,
        'daily_success_rate_trend': daily_g3_success_rate_trend,
        'daily_avg_power_trend': daily_avg_power_trend,
        'success_rate_by_assistance': { level: (g3_assistance_success[level] / g3_assistance_total[level] * 100) if g3_assistance_total[level] > 0 else 0 for level in ['NONE', 'VERBAL', 'PHYSICAL'] },
        'avg_power_by_assistance': { level: (data['total'] / data['count']) if data['count'] > 0 else 0 for level, data in g3_assistance_power.items() }
    }

def _generate_comprehensive_stats(user_id: int) -> dict:
    sessions, logs, session_assistance_map, today = _get_base_querysets(user_id)
    if sessions is None:
        default_assistance = {'NONE': 0, 'VERBAL': 0, 'PHYSICAL': 0}
        return {
            'game1': {'today_attempts': 0, 'today_success_rate': 0, 'today_play_duration_seconds': 0, 'overall_avg_success_rate': 0, 'overall_avg_response_time': 0, 'daily_success_rate_trend': [], 'daily_response_time_trend': [], 'success_rate_by_assistance': default_assistance},
            'game2': {'today_play_count': 0, 'today_play_duration_seconds': 0, 'today_avg_response_time': 0, 'overall_avg_response_time': 0, 'avg_daily_play_time_seconds': 0, 'daily_response_time_trend': [], 'daily_play_time_trend':[], 'play_time_by_assistance': default_assistance},
            'game3': {'today_attempts': 0, 'today_success_rate': 0, 'today_play_duration_seconds': 0, 'overall_avg_success_rate': 0, 'daily_success_rate_trend': [], 'daily_avg_power_trend': [], 'success_rate_by_assistance': default_assistance, 'avg_power_by_assistance': default_assistance}
        }
    
    g1_stats = _generate_game1_stats(user_id, sessions, logs, session_assistance_map, today)
    g2_stats = _generate_game2_stats(user_id, sessions, logs, session_assistance_map, today)
    g3_stats = _generate_game3_stats(user_id, sessions, logs, session_assistance_map, today)
    
    return {'game1': g1_stats, 'game2': g2_stats, 'game3': g3_stats }

# --- Other Views ---

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
    def post(self, request, *args, **kwargs):
        req_serializer = StatsRequestSerializer(data=request.data)
        if not req_serializer.is_valid():
            return Response(req_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        user_id = req_serializer.validated_data['user_id']
        statistics_data = _generate_comprehensive_stats(user_id)
        try:
            user = User.objects.get(user_id=user_id)
            analysis_data = { 'game1_analysis': user.game1_analysis, 'game2_analysis': user.game2_analysis, 'game3_analysis': user.game3_analysis, }
        except User.DoesNotExist:
            analysis_data = { 'game1_analysis': {}, 'game2_analysis': {}, 'game3_analysis': {}, }
        response_data = { 'statistics': statistics_data, **analysis_data }
        serializer = UserStatsWithAnalysisSerializer(data=response_data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class DetectEmotionView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = DetectEmotionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        image_data = serializer.validated_data['image']
        target_emotion = serializer.validated_data['target_emotion']
        header, encoded = image_data.split(",", 1)
        image_content = base64.b64decode(encoded)
        client = vision.ImageAnnotatorClient()
        image = vision.Image(content=image_content)
        response = client.face_detection(image=image)
        face_annotations = response.face_annotations
        if not face_annotations:
            return Response({"error": "No face detected"}, status=status.HTTP_400_BAD_REQUEST)
        
        is_match = False
        if target_emotion == 'happy': is_match = face_annotations[0].joy_likelihood >= 3
        elif target_emotion == 'sad': is_match = face_annotations[0].sorrow_likelihood >= 3
        elif target_emotion == 'surprised': is_match = face_annotations[0].surprise_likelihood >= 3
        elif target_emotion == 'angry': is_match = face_annotations[0].anger_likelihood >= 3
        
        return Response({"is_match": is_match}, status=status.HTTP_200_OK)

# --- Refactored AI Analysis Views ---

class BaseAnalyzeGameStatsView(APIView):
    game_key = None
    game_name = None

    def get_game_data(self, user_id, sessions, logs, session_assistance_map, today):
        raise NotImplementedError("Subclasses must implement get_game_data.")

    def create_analysis_prompt(self, game_data: dict) -> str:
        data_string = json.dumps(game_data, indent=4, ensure_ascii=False, cls=DateEncoder)
        
        # [수정] AI가 직접 단위를 변환하도록 프롬프트를 대폭 수정
        prompt = f"""
        You are a supportive developmental coach specializing in games for children with Autism Spectrum Disorder (ASD).
        Your primary goal is to empower parents by helping them see and celebrate their child's progress, no matter how small.
        You must respond in a deeply warm, hopeful, and encouraging tone.

        **CRITICAL INSTRUCTIONS:**
        1. Time values in the data are in MILLISECONDS (ms). In your summary, you MUST convert them to SECONDS (divided by 1000, rounded to one decimal place). For example, 5382ms should be reported as "5.4 seconds".
        2. **Do not use any placeholders like '[Child's Name]'.** Focus entirely on the performance and what it signifies.

        Here is the statistical data from the '{self.game_name}' game session:
        Data:
        ```json
        {data_string}
        ```

        Please analyze this data and identify the **single most positive sign of progress or effort**. 
        Summarize this finding as a warm message of praise and hope for the parent.
        Your message should be **exactly 3 lines long**, explain **why** this data point is a positive milestone, and include the key numbers (in seconds, if applicable).

        The analysis must be in English and formatted as a JSON object with the key "notable_points".
        """
        return prompt

    def post(self, request, *args, **kwargs):
        req_serializer = StatsRequestSerializer(data=request.data)
        if not req_serializer.is_valid():
            return Response(req_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        user_id = req_serializer.validated_data['user_id']
        
        try:
            sessions, logs, session_assistance_map, today = _get_base_querysets(user_id)
            if sessions is None:
                return Response({"error": f"No stats data found for User ID {user_id}."}, status=status.HTTP_404_NOT_FOUND)
            
            game_data = self.get_game_data(user_id, sessions, logs, session_assistance_map, today)
            
            gemini_api_key = os.getenv("GEMINI_API_KEY")
            if not gemini_api_key:
                raise ValueError("GEMINI_API_KEY is not set in the .env file.")
            
            prompt = self.create_analysis_prompt(game_data)
            
            # 백그라운드에서 AI 분석 실행
            import threading
            thread = threading.Thread(target=self._run_ai_analysis, args=(user_id, prompt, gemini_api_key))
            thread.start()
            
            # 즉시 응답 반환
            return Response({
                "message": f"AI analysis for {self.game_name} for User ID {user_id} has been started in the background."
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _run_ai_analysis(self, user_id, prompt, gemini_api_key):
        """백그라운드에서 실행될 AI 분석 메서드"""
        try:
            genai.configure(api_key=gemini_api_key)
            model = genai.GenerativeModel('gemini-1.5-pro-latest')
            
            response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
            analysis_result = json.loads(response.text)

            user = User.objects.get(user_id=user_id)
            setattr(user, f'{self.game_key}_analysis', analysis_result)
            user.save()
            
            print(f"AI analysis for {self.game_name} for User ID {user_id} completed and saved successfully.")
            
        except Exception as e:
            print(f"Error in background AI analysis for User ID {user_id}: {e}")

class AnalyzeGame1StatsView(BaseAnalyzeGameStatsView):
    game_key = 'game1'
    game_name = 'Look at That! (Attention & Eye Contact)'
    
    def get_game_data(self, user_id, sessions, logs, session_assistance_map, today):
        return _generate_game1_stats(user_id, sessions, logs, session_assistance_map, today)

class AnalyzeGame2StatsView(BaseAnalyzeGameStatsView):
    game_key = 'game2'
    game_name = 'Making Faces (Emotional Expression)'
    
    def get_game_data(self, user_id, sessions, logs, session_assistance_map, today):
        return _generate_game2_stats(user_id, sessions, logs, session_assistance_map, today)

class AnalyzeGame3StatsView(BaseAnalyzeGameStatsView):
    game_key = 'game3'
    game_name = 'Ball Toss (Interaction & Motor Skills)'

    def get_game_data(self, user_id, sessions, logs, session_assistance_map, today):
        return _generate_game3_stats(user_id, sessions, logs, session_assistance_map, today)


# --- Q-Learning Views ---
agent = QLearningAgent(actions=[0, 1, 2])
difficulty_map = {0: 'easy', 1: 'normal', 2: 'hard'}

class Game3RLDifficultyView(APIView):
    def post(self, request):
        user_id = request.data.get('user_id')
        if user_id is None:
            return Response({"error": "user_id is required"}, status=status.HTTP_400_BAD_REQUEST)
        current_state = get_user_state(user_id)
        action = agent.choose_action(current_state)
        recommended_difficulty = difficulty_map[action]
        return Response({ "recommended_difficulty": recommended_difficulty, "action": action, "current_state": current_state })

    def put(self, request):
        session_id = request.data.get('session_id')
        initial_state = request.data.get('initial_state')
        action = request.data.get('action')
        if None in [session_id, initial_state, action]:
            return Response({"error": "session_id, initial_state, action are required"}, status=status.HTTP_400_BAD_REQUEST)
        reward, next_state = calculate_reward_and_next_state(session_id)
        if reward is None:
            return Response({"error": "Invalid session_id or no logs found"}, status=status.HTTP_400_BAD_REQUEST)
        agent.update_q_table(float(initial_state), int(action), reward, next_state)
        return Response({"message": "Q-table updated successfully."})