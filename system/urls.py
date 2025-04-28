# system/urls.py

from django.urls import path
from . import views

urlpatterns = [
    path('api/system/hosts/', views.get_hosts, name='api_hosts'),
    path('api/system/hosts/<uuid:host_id>/metrics/', views.get_host_metrics, name='api_host_metrics'),
    path('api/system/hosts/<uuid:host_id>/', views.get_host_details, name='api_host_details'),
    path('api/system/hosts/<uuid:host_id>/metrics/history/', views.get_host_metrics_history, name='api_host_metrics_history'),
    path('api/system/hosts/<uuid:host_id>/metrics/available/', views.get_host_available_metrics, name='api_host_available_metrics'),
]