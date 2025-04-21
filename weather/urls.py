from django.urls import path
from . import views

app_name = 'weather'

urlpatterns = [
    path('dashboard/', views.weather_dashboard, name='dashboard'),
    path('api/weather/receive/', views.receive_weather_data, name='receive_data'),
]
