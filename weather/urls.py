from django.urls import path
from . import views

app_name = 'weather'

urlpatterns = [
    path('api/weather/receive/', views.receive_weather_data, name='receive_weather_data'),
    path('api/weather/current/', views.get_current_weather, name='get_current_weather'),
    path('weather/dashboard/', views.weather_dashboard, name='dashboard'),
]
