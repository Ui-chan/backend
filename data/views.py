from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from django.db.models import Avg, Count, Sum, F, Case, When
from django.db.models.functions import TruncDate
from collections import defaultdict
from google.cloud import vision
import base64
from .serializers import * # 새로 추가
import google.generativeai as genai
import os
import json
from dotenv import load_dotenv
from openai import OpenAI

from games.models import GameSession, GameInteractionLog 
from .models import ChecklistResult
from users.models import User  
from .serializers import *
from datetime import date # <<<<<<< 1. 이 부분을 추가해주세요.


# ▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼
class DateEncoder(json.JSONEncoder):
    """ date 객체를 JSON으로 변환하기 위한 클래스 """
    def default(self, o):
        if isinstance(o, date):
            return o.isoformat() # date 객체를 'YYYY-MM-DD' 형식의 문자열로 변환
        return super().default(o)
# ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲

def _generate_comprehensive_stats(user_id: int) -> dict:
    """
    주어진 사용자에 대한 종합 통계 데이터를 생성합니다. (내부 헬퍼 함수)
    
    Args:
        user_id (int): 통계를 생성할 사용자의 ID

    Returns:
        dict: 모든 게임에 대한 구조화된 통계 데이터가 담긴 딕셔너리
    """
    today = timezone.now().date()

    sessions = GameSession.objects.filter(user_id=user_id)
    if not sessions.exists():
        # 사용자의 게임 기록이 없는 경우, 기본 데이터 구조를 반환합니다.
        default_assistance = {'NONE': 0, 'VERBAL': 0, 'PHYSICAL': 0}
        return {
            'game1': {'today_attempts': 0, 'today_success_rate': 0, 'today_play_duration_seconds': 0, 'overall_avg_success_rate': 0, 'overall_avg_response_time': 0, 'daily_success_rate_trend': [], 'daily_response_time_trend': [], 'success_rate_by_assistance': default_assistance},
            'game2': {'today_play_count': 0, 'today_play_duration_seconds': 0, 'today_avg_response_time': 0, 'overall_avg_response_time': 0, 'avg_daily_play_time_seconds': 0, 'daily_response_time_trend': [], 'play_time_by_assistance': default_assistance},
            'game3': {'today_attempts': 0, 'today_success_rate': 0, 'today_play_duration_seconds': 0, 'overall_avg_success_rate': 0, 'daily_success_rate_trend': [], 'daily_avg_power_trend': [], 'success_rate_by_assistance': default_assistance, 'avg_power_by_assistance': default_assistance}
        }
        
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
    daily_response_time_trend_g2 = list(
        g2_logs
        .filter(response_time_ms__isnull=False)
        .annotate(date=TruncDate('timestamp'))
        .values('date')
        .annotate(value=Avg('response_time_ms'))
        .values('date', 'value')
        .order_by('date')
    )
    g2_today_sessions = g2_sessions.filter(session_start_time__date=today, session_end_time__isnull=False)
    today_play_duration_agg = g2_today_sessions.aggregate(total=Sum(F('session_end_time') - F('session_start_time')))['total']
    total_play_time_agg = g2_sessions.exclude(session_end_time__isnull=True).aggregate(total=Sum(F('session_end_time') - F('session_start_time')))['total']
    total_play_days = g2_sessions.annotate(date=TruncDate('session_start_time')).values('date').distinct().count()

    # ✅ 날짜별 플레이 시간 추이 계산
    daily_g2_play_time = (
        g2_sessions
        .exclude(session_end_time__isnull=True)
        .annotate(date=TruncDate('session_start_time'))
        .values('date')
        .annotate(total_duration=Sum(F('session_end_time') - F('session_start_time')))
    )

    daily_play_time_trend_g2 = [
        {
            'date': entry['date'],
            'value': entry['total_duration'].total_seconds() if entry['total_duration'] else 0
        }
        for entry in daily_g2_play_time
    ]

    g2_stats = {
        'today_play_count': g2_today_sessions.count(),
        'today_play_duration_seconds': today_play_duration_agg.total_seconds() if today_play_duration_agg else 0,
        'today_avg_response_time': g2_logs.filter(timestamp__date=today).aggregate(avg=Avg('response_time_ms'))['avg'] or 0,
        'overall_avg_response_time': g2_logs.aggregate(avg=Avg('response_time_ms'))['avg'] or 0,
        'avg_daily_play_time_seconds': (total_play_time_agg.total_seconds() / total_play_days) if total_play_days > 0 else 0,
        'daily_response_time_trend': daily_response_time_trend_g2,
        'daily_play_time_trend': daily_play_time_trend_g2,  # ✅ 새 필드 추가
        'play_time_by_assistance': {
            level: (
                g2_sessions
                .filter(assistance_level=level, session_end_time__isnull=False)
                .aggregate(total=Sum(F('session_end_time') - F('session_start_time')))['total']
                .total_seconds()
            ) if g2_sessions.filter(assistance_level=level).exists() else 0
            for level in ['NONE', 'VERBAL', 'PHYSICAL']
        }
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
    
    # 최종 데이터 구조화
    processed_data = {'game1': g1_stats, 'game2': g2_stats, 'game3': g3_stats }
    return processed_data


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
    사용자의 통계 데이터와 저장된 AI 분석 결과를 함께 반환하는 API
    """
    def post(self, request, *args, **kwargs):
        # 1. 요청 데이터 검증
        req_serializer = StatsRequestSerializer(data=request.data)
        if not req_serializer.is_valid():
            return Response(req_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        user_id = req_serializer.validated_data['user_id']
        
        # 2. 헬퍼 함수를 호출하여 통계 데이터 생성
        statistics_data = _generate_comprehensive_stats(user_id)
        
        # 3. User 모델에서 AI 분석 결과 조회
        try:
            user = User.objects.get(user_id=user_id)
            analysis_data = {
                'game1_analysis': user.game1_analysis,
                'game2_analysis': user.game2_analysis,
                'game3_analysis': user.game3_analysis,
            }
        except User.DoesNotExist:
            # 사용자가 없으면 분석 결과는 비워둡니다.
            analysis_data = {
                'game1_analysis': {},
                'game2_analysis': {},
                'game3_analysis': {},
            }

        # 4. 통계 데이터와 분석 결과를 합쳐 최종 응답 데이터 구조 생성
        response_data = {
            'statistics': statistics_data,
            **analysis_data  # 딕셔너리 합치기
        }
        
        # 5. 새로 만든 최상위 시리얼라이저로 결과 직렬화 및 반환
        serializer = UserStatsWithAnalysisSerializer(data=response_data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    

class DetectEmotionView(APIView):
    """
    이미지, 목표 감정, 그리고 반응 시간을 받아 일치 여부를 분석하는 API
    """
    def post(self, request, *args, **kwargs):
        # 이제 Serializer가 image, target_emotion, response_time_ms를 모두 검증합니다.
        serializer = DetectEmotionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        image_data = serializer.validated_data['image']
        target_emotion = serializer.validated_data['target_emotion']
        response_time_ms = serializer.validated_data['response_time_ms']
        # response_time_ms 값도 validated_data에 포함되지만, 이 View의 핵심 로직(감정 분석)에는
        # 사용되지 않으므로 따로 변수로 추출할 필요는 없습니다. 
        # 만약 이 값을 DB에 저장하거나 다른 용도로 사용하려면 아래와 같이 추출할 수 있습니다.
        # response_time_ms = serializer.validated_data['response_time_ms']
            
        header, encoded = image_data.split(",", 1)
        image_content = base64.b64decode(encoded)

        client = vision.ImageAnnotatorClient()
        image = vision.Image(content=image_content)
        response = client.face_detection(image=image)
        face_annotations = response.face_annotations

        if not face_annotations:
            return Response({"error": "No face detected"}, status=status.HTTP_400_BAD_REQUEST)

        likelihood_name = ('UNKNOWN', 'VERY_UNLIKELY', 'UNLIKELY', 'POSSIBLE', 'LIKELY', 'VERY_LIKELY')
        emotions = face_annotations[0]
        
        target_likelihood_str = 'UNKNOWN'
        is_match = False

        if target_emotion == 'happy':
            target_likelihood_str = likelihood_name[emotions.joy_likelihood]
            is_match = target_likelihood_str in ['POSSIBLE', 'LIKELY', 'VERY_LIKELY']

        elif target_emotion == 'sad':
            target_likelihood_str = likelihood_name[emotions.sorrow_likelihood]
            is_match = target_likelihood_str in ['POSSIBLE', 'LIKELY', 'VERY_LIKELY']

        elif target_emotion == 'surprised':
            target_likelihood_str = likelihood_name[emotions.surprise_likelihood]
            is_match = target_likelihood_str in ['POSSIBLE', 'LIKELY', 'VERY_LIKELY']

        elif target_emotion == 'angry':
            target_likelihood_str = likelihood_name[emotions.anger_likelihood]
            is_match = target_likelihood_str in ['POSSIBLE', 'LIKELY', 'VERY_LIKELY']
        
        return Response({
            "detected_emotion": target_emotion,
            "target_emotion" : target_emotion,
            "is_match": is_match,
            "response_time_ms" : response_time_ms,
            "target_likelihood": target_likelihood_str
        }, status=status.HTTP_200_OK)
    
class AnalyzeAndSaveStatsView(APIView):
    """
    사용자의 통계 데이터를 Gemini AI로 분석하고 그 결과를 DB에 저장하는 API.
    """
    def post(self, request, *args, **kwargs):
        req_serializer = StatsRequestSerializer(data=request.data)
        if not req_serializer.is_valid():
            return Response(req_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        user_id = 2 # 요청에서는 user_id=2를 사용

        # 1. 통계 데이터 생성
        try:
            stats_data = _generate_comprehensive_stats(user_id)
            if not stats_data or not stats_data.get('game1'):
                 return Response({"error": f"User ID {user_id}에 대한 통계 데이터가 없습니다."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": f"통계 데이터 생성 중 오류 발생: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # 2. Gemini 클라이언트 설정 🤖
        try:
            gemini_api_key = os.getenv("GEMINI_API_KEY")
            if not gemini_api_key:
                raise ValueError("GEMINI_API_KEY가 .env 파일에 설정되지 않았습니다.")
            genai.configure(api_key=gemini_api_key)
        except Exception as e:
            return Response({"error": f"Gemini 클라이언트 설정 실패: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        analysis_results = {}
        generation_config = {"response_mime_type": "application/json"} # JSON 출력 모드 설정
        model = genai.GenerativeModel('gemini-1.5-pro-latest') # 사용할 모델 선택

        # 3. 각 게임별로 AI 분석 수행
        for game_key, game_data in stats_data.items():
            prompt = self.create_analysis_prompt(game_key, game_data)

            try:
                # Gemini API 호출
                response = model.generate_content(
                    prompt,
                    generation_config=generation_config
                )
                
                # Gemini 응답(JSON 형식)을 파싱
                ai_response_content = response.text
                analysis_results[game_key] = json.loads(ai_response_content)

            except Exception as e:
                return Response({"error": f"{game_key} 분석 중 Gemini API 오류 발생: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # 4. 분석 결과를 데이터베이스에 저장
        try:
            user = User.objects.get(user_id=user_id)
            user.game1_analysis = analysis_results.get('game1', {})
            user.game2_analysis = analysis_results.get('game2', {})
            user.game3_analysis = analysis_results.get('game3', {})
            user.save()
        except User.DoesNotExist:
            return Response({"error": f"User ID {user_id}를 찾을 수 없습니다."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": f"분석 결과 저장 중 오류 발생: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # 5. 성공 응답 반환
        return Response({
            "message": f"User ID {user_id}에 대한 Gemini AI 분석이 완료되었고 결과가 성공적으로 저장되었습니다.",
            "analysis_results": analysis_results
        }, status=status.HTTP_200_OK)

    def create_analysis_prompt(self, game_key: str, game_data: dict) -> str:
        """AI 분석을 위한 프롬프트를 생성하는 헬퍼 메서드"""
        game_name_map = {
            'game1': 'Look at That! (Attention & Eye Contact)',
            'game2': 'Making Faces (Emotional Expression)',
            'game3': 'Ball Toss (Interaction & Motor Skills)'
        }
        game_name = game_name_map.get(game_key, game_key)
        data_string = json.dumps(game_data, indent=4, ensure_ascii=False, cls=DateEncoder)

        prompt = f"""
        You are an expert data analyst for developmental games designed to help children with Autism Spectrum Disorder (ASD). 
        You must respond in a warm, hopeful, and encouraging tone so that parents can easily understand and be encouraged by their child's growth.

        The following is the statistical data for a child's performance in the '{game_name}' game.

        Data:
        ```json
        {data_string}
        ```

        Based on this data, please find **one positive feature or notable point** that best showcases the child's effort and growth. 
        Summarize this feature as a message for the parents in **exactly 3 lines, including key numerical values**.

        (Example: 'Today, your child showed wonderful concentration. Notably, their success rate reached 70% with only verbal help (VERBAL), which is a positive sign that their willingness to listen to instructions and try things on their own is growing stronger. Consistently praising this type of interaction will be a great help in boosting their confidence.')

        The analysis must be provided in English and formatted as a JSON object (`"response_mime_type": "application/json"`) as requested. The output JSON object must have the following key:
        - "notable_points"
        """
        return prompt