from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Create a router for ViewSet
router = DefaultRouter()
router.register(r'data', views.SolarDataViewSet, basename='solar-data')

urlpatterns = [
    # API endpoints with /api/solar/ prefix
    path('api/solar/', include(router.urls)),
    
    # Upload and cleanup endpoints
    path('api/solar/upload/', views.solar_data_upload, name='solar-upload'),
    path('api/solar/cleanup/', views.cleanup_solar_data, name='solar-cleanup'),
]
