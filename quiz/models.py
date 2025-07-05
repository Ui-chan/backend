from django.db import models

class Quiz(models.Model):
    quiz_id = models.AutoField(primary_key=True)
    quiz_image = models.CharField(max_length=255, blank=True, null=True)
    quiz_answer = models.CharField(max_length=255, blank=True, null=True)
    quiz_list = models.JSONField(blank=True, null=True)  # MySQL도 지원

    class Meta:
        db_table = 'quiz'
