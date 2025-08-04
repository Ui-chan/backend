from django.urls import path
from .views import *

urlpatterns = [
    # item/
    path('all/', ItemListView.as_view()),
    path('buy/', ItemPurchaseView.as_view()),
    path('base-setting/', UpdateBaseView.as_view()),
]