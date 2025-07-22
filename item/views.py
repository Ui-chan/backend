from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Item
from users.models import User # User 모델을 가져오기 위해 추가합니다.
from .serializers import *

class ItemListView(APIView):
    def get(self, request):
        items = Item.objects.all()
        serializer = ItemSerializer(items, many=True)
        return Response(serializer.data)


class AddItemToUserView(APIView):
    def post(self, request):
        serializer = AddItemToUserSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({'message': '아이템이 성공적으로 추가되었습니다.'}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

class UpdateBaseView(APIView):
    def post(self, request):
        serializer = UpdateBaseSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user = serializer.validated_data['user_instance']
        item_name = serializer.validated_data['item_name']

        if serializer.validated_data['is_character']:
            try:
                item = Item.objects.get(item_name=item_name, item_type=1)
            except Item.DoesNotExist:
                return Response({'error': '해당 캐릭터 아이템이 존재하지 않습니다.'}, status=status.HTTP_404_NOT_FOUND)

            # ✅ 캐릭터 이름 및 이미지 업데이트
            user.base_character_name = item.item_name
            user.base_character_img = item.item_img
            user.save()

            return Response({'message': '캐릭터가 성공적으로 업데이트되었습니다.'}, status=status.HTTP_200_OK)

        elif serializer.validated_data['is_background']:
            try:
                item = Item.objects.get(item_name=item_name, item_type=2)
            except Item.DoesNotExist:
                return Response({'error': '해당 배경 아이템이 존재하지 않습니다.'}, status=status.HTTP_404_NOT_FOUND)

            # ✅ 배경 이름 및 이미지 업데이트
            user.base_background_name = item.item_name
            user.base_background_img = item.item_detail_img
            user.save()

            return Response({'message': '배경이 성공적으로 업데이트되었습니다.'}, status=status.HTTP_200_OK)

        else:
            return Response({'error': 'item_name의 유형을 확인할 수 없습니다.'}, status=status.HTTP_400_BAD_REQUEST)
        
class BaseCharacterDetailView(APIView):
    """
    user_id를 받아 해당 유저의 대표 캐릭터 아이템 상세 정보를 반환하는 API
    """
    def post(self, request):
        # 1. 입력된 user_id 유효성 검사
        serializer = UserIdSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user_id = serializer.validated_data['user_id']

        # 2. 해당 유저 찾기
        try:
            user = User.objects.get(user_id=user_id)
        except User.DoesNotExist:
            return Response({'error': '해당 유저를 찾을 수 없습니다.'}, status=status.HTTP_404_NOT_FOUND)

        # 3. 유저의 대표 캐릭터 이름 가져오기
        base_character_name = user.base_character_name
        if not base_character_name:
            return Response({'error': '유저에게 설정된 대표 캐릭터가 없습니다.'}, status=status.HTTP_400_BAD_REQUEST)

        # 4. 아이템 테이블에서 해당 캐릭터 아이템 찾기
        try:
            item = Item.objects.get(item_name=base_character_name, item_type=1) # item_type=1은 캐릭터를 의미
        except Item.DoesNotExist:
            return Response({'error': '대표 캐릭터에 해당하는 아이템을 찾을 수 없습니다.'}, status=status.HTTP_404_NOT_FOUND)
        
        # 5. 아이템의 item_detail_img 필드 반환
        return Response({'item_detail_img': item.item_detail_img}, status=status.HTTP_200_OK)