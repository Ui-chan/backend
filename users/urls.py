from django.urls import path
from .views import *

urlpatterns = [
    path('signup/', UserSignupView.as_view(), name='user_signup'),
    path('detail/', UserDetailView.as_view(), name='user_detail'),
    path('login/', UserLoginView.as_view(), name='user-login'),
    path('stamps/', UserStampView.as_view()),
    path('update-equipped/', UpdateEquippedItemsView.as_view()),
]