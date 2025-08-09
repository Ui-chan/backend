from rest_framework import serializers
from .models import User

class UserSignupSerializer(serializers.ModelSerializer):
    age = serializers.IntegerField(required=True, error_messages={
        'required': 'Age is required.',
        'invalid': 'Age must be a valid number.'
    })

    class Meta:
        model = User
        fields = '__all__'
        read_only_fields = ['user_id']

    def validate_username(self, value):
        if not value.strip():
            raise serializers.ValidationError("Username cannot be empty.")
        return value

    def validate_password(self, value):
        if not value.strip():
            raise serializers.ValidationError("Password cannot be empty.")
        return value

    def create(self, validated_data):
        # --- 이 부분을 수정합니다 ---
        # 회원가입 시 기본 캐릭터 이름과 이미지를 설정합니다.
        validated_data['base_character_name'] = ['dog']
        validated_data['base_character_img'] = ['https://iccas-zerodose.s3.ap-northeast-2.amazonaws.com/character/dog1/dog_main.png']

        validated_data['base_background_img'] = 'https://iccas-zerodose.s3.ap-northeast-2.amazonaws.com/background/farm/farm.jpg'
        
        validated_data['store_character'] = ['dog']
        validated_data['store_background'] = ['farm']
        # 기본 배경 이름은 User 모델에 설정된 default 값('yard')을 따릅니다.
        return User.objects.create(**validated_data)


class UserDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = '__all__'