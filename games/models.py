from django.db import models
from django.utils import timezone
from users.models import User # users 앱의 User 모델을 import

class GameSession(models.Model):
    session_id = models.AutoField(primary_key=True)
    user_id = models.IntegerField()
    game_id = models.IntegerField()
    session_start_time = models.DateTimeField(default=timezone.now)
    session_end_time = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    assistance_level = models.CharField(max_length=20, null=True, blank=True)

    class Meta:
        db_table = 'game_session'
        ordering = ['-session_start_time']

    def __str__(self):
        return f"Session {self.session_id} for User {self.user_id}"

class GameInteractionLog(models.Model):
    log_id = models.AutoField(primary_key=True)
    session_id = models.IntegerField()
    timestamp = models.DateTimeField(default=timezone.now)
    is_successful = models.BooleanField()
    response_time_ms = models.IntegerField(null=True, blank=True)
    interaction_data = models.JSONField()
    game_type = models.IntegerField(default=0)  # 새로 추가된 필드

    class Meta:
        db_table = 'game_interaction_log'
        ordering = ['timestamp']

    def __str__(self):
        return f"Log {self.log_id} for Session {self.session_id}"
    
class FirstGameQuiz(models.Model):
    quiz_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    prompt_text = models.CharField(max_length=255, help_text="예: 🍎 빨간 사과는 어디 있지?")
    items = models.JSONField()
    correct_answer = models.CharField(max_length=100)
    is_ready = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'first_game_quizzes'

    def __str__(self):
        return self.prompt_text