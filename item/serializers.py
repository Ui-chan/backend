from rest_framework import serializers
from .models import Item
from users.models import User

class ItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = Item
        fields = '__all__'

class ItemPurchaseSerializer(serializers.Serializer):
    """아이템 구매 처리를 위한 Serializer"""
    user_id = serializers.IntegerField()
    item_id = serializers.IntegerField()

    def validate(self, data):
        try:
            user = User.objects.get(pk=data['user_id'])
            item = Item.objects.get(pk=data['item_id'])
        except User.DoesNotExist:
            raise serializers.ValidationError("해당 유저를 찾을 수 없습니다.")
        except Item.DoesNotExist:
            raise serializers.ValidationError("해당 아이템을 찾을 수 없습니다.")

        # 포인트 확인
        if (user.point or 0) < item.price:
            raise serializers.ValidationError("포인트가 부족합니다.")

        # 이미 소유했는지 확인
        item_name = item.item_name
        if item.item_type == 1: # 캐릭터
            if user.store_character and item_name in user.store_character:
                raise serializers.ValidationError("이미 보유한 캐릭터입니다.")
        elif item.item_type == 2: # 배경
            if user.store_background and item_name in user.store_background:
                raise serializers.ValidationError("이미 보유한 배경입니다.")
        
        # view에서 사용하기 위해 인스턴스를 data에 추가
        data['user'] = user
        data['item'] = item
        return data

    def create(self, validated_data):
        user = validated_data['user']
        item = validated_data['item']
        
        # 1. 포인트 차감
        user.point -= item.price
        
        # 2. 소유 목록에 아이템 추가
        if item.item_type == 1:
            # 기존 목록이 없으면 새로 만들고, 있으면 추가
            if not user.store_character:
                user.store_character = []
            user.store_character.append(item.item_name)
        
        elif item.item_type == 2:
            if not user.store_background:
                user.store_background = []
            user.store_background.append(item.item_name)
            
        user.save()
        return user
    

class UpdateBaseSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    item_name = serializers.CharField()

    def validate(self, data):
        user_id = data['user_id']
        item_name = data['item_name']

        try:
            user = User.objects.get(user_id=user_id)
        except User.DoesNotExist:
            raise serializers.ValidationError("해당 유저가 존재하지 않습니다.")

        store_characters = user.store_character or []
        store_backgrounds = user.store_background or []

        if item_name not in store_characters and item_name not in store_backgrounds:
            raise serializers.ValidationError("item_name이 유저의 보유 아이템에 존재하지 않습니다.")

        data['user_instance'] = user  # 이후에 활용하기 위해 저장
        data['is_character'] = (item_name in store_characters)
        data['is_background'] = (item_name in store_backgrounds)

        return data
    
class UserIdSerializer(serializers.Serializer):
    """
    user_id를 입력받기 위한 간단한 시리얼라이저
    """
    user_id = serializers.IntegerField(required=True)