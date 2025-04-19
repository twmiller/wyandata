# system/urls.py

from django.urls import path
from . import views

urlpatterns = [
    path('api/hosts/', views.get_hosts, name='api_hosts'),
]