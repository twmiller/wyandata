# system/urls.py

from django.urls import path
from . import views

urlpatterns = [
    path('api/hosts/', views.get_hosts, name='api_hosts'),
    path('api/hosts/<uuid:host_id>/', views.get_host_metrics, name='api_host_details'),
]