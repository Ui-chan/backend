from rest_framework import serializers
from .models import Quiz
from data.models import QuizResult  # data 앱에 있는 QuizResult 모델을 가져옵니다.

class QuizSerializer(serializers.ModelSerializer):
    """
    퀴즈 데이터를 보여주기 위한 Serializer
    """
    class Meta:
        model = Quiz
        fields = '__all__' # 모델의 모든 필드를 포함

class QuizCreateSerializer(serializers.Serializer):
    """
    퀴즈 생성을 위해 user_id를 입력받기 위한 Serializer
    """
    user_id = serializers.IntegerField()

class QuizAnswerSerializer(serializers.Serializer):
    """
    사용자의 답변(selected)을 입력받기 위한 Serializer
    """
    selected = serializers.CharField(max_length=255)



class ThirdGameResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuizResult
        # 프론트엔드에서 보낸 데이터 중, DB에 저장할 필드들을 지정합니다.
        fields = ['user_id', 'quiz_id', 'duration_seconds']

    def create(self, validated_data):
        # 데이터 생성 시, quiz_type을 3 (카드 게임)으로 고정합니다.
        validated_data['quiz_type'] = 3
        return QuizResult.objects.create(**validated_data)
    

class FirstGameResultSerializer(serializers.ModelSerializer):
    """
    1단계 게임(감정 퀴즈) 결과 저장을 위한 Serializer
    """
    class Meta:
        model = QuizResult
        # 프론트엔드에서 직접 받을 필드들을 명시합니다.
        fields = ['user_id', 'quiz_id', 'selected', 'is_correct', 'duration_seconds', 'emotion']

    def create(self, validated_data):
        # 1단계 게임이므로 quiz_type을 1로 고정하여 저장합니다.
        validated_data['quiz_type'] = 1
        return QuizResult.objects.create(**validated_data)
    

class SecondGameResultSerializer(serializers.ModelSerializer):
    """
    2단계 게임(사회성 퀴즈) 결과 저장을 위한 Serializer
    """
    theme = serializers.CharField(max_length=255, source='situation')

    class Meta:
        model = QuizResult
        # 'selected'를 필드 목록에서 제거하고, is_correct는 1 또는 0으로 받습니다.
        fields = ['user_id', 'is_correct', 'duration_seconds', 'theme']

    def create(self, validated_data):
        # 2단계 게임이므로 quiz_type을 2로 고정하여 저장합니다.
        validated_data['quiz_type'] = 2
        return QuizResult.objects.create(**validated_data)
