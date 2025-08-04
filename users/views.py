from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import User
from item.models import Item
from .serializers import UserSignupSerializer, UserDetailSerializer

class UserSignupView(APIView):
    def post(self, request):
        serializer = UserSignupSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response(UserSignupSerializer(user).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class UserDetailView(APIView):
    def post(self, request):
        user_id = request.data.get('user_id')
        if not user_id:
            return Response({'error': 'user_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            user = User.objects.get(user_id=user_id)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

        serializer = UserDetailSerializer(user)
        return Response(serializer.data)

class UserLoginView(APIView):
    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')

        if not username or not password:
            return Response({'error': 'username and password are required.'}, status=status.HTTP_400_BAD_REQUEST)

        # --- 이 부분을 수정합니다 ---
        # .get() 대신 .filter().first()를 사용하여 중복이 있어도 첫 번째 객체를 가져옵니다.
        user = User.objects.filter(username=username, password=password).first()

        # user가 존재하지 않으면 None이 반환됩니다.
        if user is None:
            return Response({'error': 'Invalid username or password.'}, status=status.HTTP_401_UNAUTHORIZED)

        serializer = UserDetailSerializer(user)
        return Response({'message': 'Login successful', 'user': serializer.data}, status=status.HTTP_200_OK)


class UserStampView(APIView):
    """
    요청 body로 받은 user_id를 기반으로 스탬프 개수를 반환하는 API
    """
    def post(self, request, *args, **kwargs):
        user_id = request.data.get('user_id')
        if not user_id:
            return Response({'error': 'user_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(pk=user_id)
            total_points = user.point or 0
            
            
            stamp_count = total_points

            return Response({
                "user_id": user.user_id,
                "username": user.username,
                "stamp_count": stamp_count
            }, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)
        
class UpdateEquippedItemsView(APIView):
    """
    사용자가 선택한 대표 캐릭터/배경을 업데이트하는 API
    (캐릭터 다중 선택 가능하도록 수정)
    """
    def post(self, request, *args, **kwargs):
        user_id = request.data.get('user_id')
        character_names = request.data.get('character_names') 
        background_name = request.data.get('background_name')

        if not user_id:
            return Response({'error': 'user_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return Response({'error': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)

        # 캐릭터 업데이트 로직 (다중 선택 처리)
        if character_names is not None:
            owned_characters = user.store_character or []
            for name in character_names:
                if name not in owned_characters:
                    return Response({'error': f'User does not own the character: {name}.'}, status=status.HTTP_400_BAD_REQUEST)

            items = Item.objects.filter(item_name__in=character_names, item_type=1)
            if len(items) != len(character_names):
                return Response({'error': 'One or more character items not found.'}, status=status.HTTP_404_NOT_FOUND)

            user.base_character_name = [item.item_name for item in items]
            user.base_character_img = [item.item_img for item in items]

        # 배경 업데이트 로직 (단일 선택 유지)
        if background_name:
            if background_name in (user.store_background or []):
                try:
                    item = Item.objects.get(item_name=background_name, item_type=2)
                    user.base_background_name = item.item_name
                    # --- 이 부분을 수정합니다 ---
                    # TextField에 이미지 URL 문자열을 직접 저장합니다.
                    user.base_background_img = item.item_img
                except Item.DoesNotExist:
                    return Response({'error': 'Item not found in item list.'}, status=status.HTTP_404_NOT_FOUND)
            else:
                return Response({'error': 'User does not own this background.'}, status=status.HTTP_400_BAD_REQUEST)
        
        user.save()
        return Response({'message': 'Equipped items updated successfully.'}, status=status.HTTP_200_OK)