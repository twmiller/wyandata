from django.urls import path
from . import views

app_name = 'solar'

urlpatterns = [
    # Update all URLs to have /api/solar/ prefix
    path('api/solar/current/', views.get_current_solar, name='api_current_solar'),
    path('api/solar/history/', views.get_solar_history, name='api_solar_history'),
    path('api/solar/daily/', views.get_daily_solar, name='api_daily_solar'),
    path('api/solar/monthly/', views.get_monthly_solar, name='api_monthly_solar'),
    path('api/solar/yearly/', views.get_yearly_solar, name='api_yearly_solar'),
    # Keep the dashboard URL as is
    path('solar/dashboard/', views.solar_dashboard, name='dashboard'),
]
