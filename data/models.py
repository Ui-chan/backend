from django.db import models
from django.utils import timezone

class ChecklistResult(models.Model):
    """
    발달 체크리스트 결과 기록을 위한 모델
    """
    result_id = models.AutoField(primary_key=True)
    user_id = models.IntegerField()
    total_score = models.IntegerField()
    critical_item_score = models.IntegerField()
    risk_level = models.CharField(max_length=50)
    recommendation = models.TextField()
    answers = models.JSONField() # 사용자의 답변 전체를 JSON으로 저장
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'checklist_results'
        ordering = ['-created_at'] # 최신 기록부터 정렬

    def __str__(self):
        return f"Result for User {self.user_id} on {self.created_at.strftime('%Y-%m-%d')}"