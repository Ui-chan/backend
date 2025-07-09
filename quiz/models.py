from django.db import models
from django.utils import timezone

class Quiz(models.Model):
    quiz_id = models.AutoField(primary_key=True)
    user_id = models.IntegerField(blank=True, null=True)
    quiz_image = models.TextField(blank=True, null=True)
    correct_answer = models.CharField(max_length=255, blank=True, null=True)
    answer_list = models.JSONField(blank=True, null=True)
    selected = models.CharField(max_length=255, blank=True, null=True)
    is_correct = models.CharField(max_length=10, blank=True, null=True)

    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'quiz'