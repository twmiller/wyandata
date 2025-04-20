from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
# Add your viewsets here if any

urlpatterns = [
    path('', include(router.urls)),
    path('upload/', views.solar_data_upload, name='solar-data-upload'),
    path('cleanup/', views.cleanup_solar_data, name='solar-data-cleanup'),
]
