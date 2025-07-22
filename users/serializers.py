from rest_framework import serializers
from .models import User

class UserSignupSerializer(serializers.ModelSerializer):
    # age 필드를 명시적으로 정의하여 필수로 만듦
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
        return User.objects.create(**validated_data)

class UserDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = '__all__'