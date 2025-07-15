from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import *

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
        age = request.data.get('age')

        if not username or age is None:
            return Response({'error': 'username and age are required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(username=username, age=age)
        except User.DoesNotExist:
            return Response({'error': 'Invalid username or age.'}, status=status.HTTP_401_UNAUTHORIZED)

        serializer = UserDetailSerializer(user)
        return Response({'message': 'Login successful', 'user': serializer.data}, status=status.HTTP_200_OK)
