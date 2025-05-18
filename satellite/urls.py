from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Create a router for the API
router = DefaultRouter()
router.register(r'emwin', views.EMWINFileViewSet)
router.register(r'stations', views.EMWINStationViewSet)
router.register(r'products', views.EMWINProductViewSet)

urlpatterns = [
    # API endpoints with the prefix specified in the main urls.py
    path('api/satellite/', include(router.urls)),
]
