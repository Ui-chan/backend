from django.urls import path
from .views import *

urlpatterns = [
    # item/
    path('all/', ItemListView.as_view()),
    path('buy/', AddItemToUserView.as_view()),
    path('base-setting/', UpdateBaseView.as_view()),
    path('userid-to-emotions/', BaseCharacterDetailView.as_view()),
]