from django.urls import path
from . import views

app_name = 'weather'

urlpatterns = [
    path('api/weather/receive/', views.receive_weather_data, name='receive_weather_data'),
    path('api/weather/current/', views.get_current_weather, name='get_current_weather'),
    path('api/weather/recent/', views.get_recent_readings, name='get_recent_readings'),
    path('api/weather/daily/', views.get_daily_weather, name='get_daily_weather'),
    path('api/weather/monthly/', views.get_monthly_weather, name='get_monthly_weather'),
    path('weather/dashboard/', views.weather_dashboard, name='dashboard'),
]
