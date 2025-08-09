# data/rl_utils.py

from games.models import GameSession, GameInteractionLog

def get_user_state(user_id, game_type=3):
    """ 사용자의 현재 '상태' (최근 평균 throw_power)를 계산합니다. """
    # 해당 유저의 3번 게임 세션 ID들을 모두 가져옵니다.
    user_sessions = GameSession.objects.filter(
        user_id=user_id, 
        game_id=game_type
    ).values_list('session_id', flat=True)
    
    # 해당 세션들에 속한 로그들을 최신 20개 가져옵니다.
    # [수정] session__session_id__in -> session_id__in 으로 쿼리 변경
    logs = GameInteractionLog.objects.filter(session_id__in=list(user_sessions)).order_by('-timestamp')[:20]

    if not logs:
        return 50.0  # 기록이 없으면 중간값 50으로 시작

    total_power = sum(log.interaction_data.get('throw_power', 0) for log in logs)
    count = sum(1 for log in logs if 'throw_power' in log.interaction_data)
    
    return total_power / count if count > 0 else 50.0

def calculate_reward_and_next_state(session_id):
    """ 한 게임 세션의 '보상'과 '다음 상태'를 계산합니다. """
    logs = GameInteractionLog.objects.filter(session_id=session_id)
    total_throws = logs.count()

    if total_throws == 0:
        return None, None

    # 보상 계산
    successful_throws = logs.filter(is_successful=True).count()
    success_rate = successful_throws / total_throws
    reward = 1.0 if success_rate >= 0.5 else -1.0

    # 다음 상태(next_state) 계산
    total_power = sum(log.interaction_data.get('throw_power', 0) for log in logs)
    next_state = total_power / total_throws

    return reward, next_state