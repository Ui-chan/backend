from django.db import models
from django.utils import timezone

class GameSession(models.Model):
    session_id = models.AutoField(primary_key=True)
    user_id = models.IntegerField()
    game_id = models.IntegerField()
    session_start_time = models.DateTimeField(default=timezone.now)
    session_end_time = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    # assistance_level 필드를 GameSession으로 이동
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
    # assistance_level 필드 제거
    interaction_data = models.JSONField()

    class Meta:
        db_table = 'game_interaction_log'
        ordering = ['timestamp']

    def __str__(self):
        return f"Log {self.log_id} for Session {self.session_id}"