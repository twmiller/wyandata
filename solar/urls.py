from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Create a router for REST API
router = DefaultRouter()
router.register(r'data', views.SolarDataViewSet, basename='solar-data')

urlpatterns = [
    # REST API endpoints
    path('', include(router.urls)),
    
    # Upload endpoint
    path('upload/', views.solar_data_upload, name='solar-data-upload'),
]
