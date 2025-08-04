from django.db import models

class User(models.Model):
    user_id = models.AutoField(primary_key=True)
    username = models.CharField(max_length=255, null=True, blank=True)
    password = models.CharField(max_length=255, null=True, blank=True)
    age = models.IntegerField(null=True, blank=True)
    point = models.IntegerField(default=0, null=True, blank=True)
    base_character_name = models.JSONField(null=True, blank=True)
    base_character_img = models.JSONField(null=True, blank=True)
    base_background_name = models.CharField(max_length=50, default='farm', null=True, blank=True)
    base_background_img = models.TextField(null=True, blank=True)  # 새로 추가한 필드
    store_character = models.JSONField(null=True, blank=True)
    store_background = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'users'
