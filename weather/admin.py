from django.contrib import admin
from .models import OutdoorWeatherReading, IndoorSensor, DailyWeatherSummary, MonthlyWeatherSummary

@admin.register(OutdoorWeatherReading)
class OutdoorWeatherReadingAdmin(admin.ModelAdmin):
    list_display = ('time', 'model', 'sensor_id', 'temperature_F', 'humidity', 
                    'wind_direction_cardinal', 'wind_avg_mph', 'wind_max_mph', 
                    'rain_inches', 'rainfall_since_previous')
    list_filter = ('model', 'sensor_id')
    date_hierarchy = 'time'
    search_fields = ('model', 'sensor_id')
    readonly_fields = ('temperature_F', 'wind_avg_mph', 'wind_max_mph', 
                      'rain_inches', 'rainfall_since_previous', 'wind_direction_cardinal')

@admin.register(IndoorSensor)
class IndoorSensorAdmin(admin.ModelAdmin):
    list_display = ('time', 'model', 'sensor_id', 'temperature_F', 'humidity', 'pressure_hPa', 'battery_ok')
    list_filter = ('model', 'sensor_id')
    date_hierarchy = 'time'
    search_fields = ('model', 'sensor_id')
    readonly_fields = ('temperature_F', 'pressure_inHg')

@admin.register(DailyWeatherSummary)
class DailyWeatherSummaryAdmin(admin.ModelAdmin):
    list_display = ('date', 'min_temp_f', 'max_temp_f', 'avg_temp_f', 'total_rainfall_inches', 
                   'max_wind_speed_mph', 'predominant_wind_direction')
    readonly_fields = ('min_temp_f', 'max_temp_f', 'avg_temp_f', 'total_rainfall_inches')
    date_hierarchy = 'date'

@admin.register(MonthlyWeatherSummary)
class MonthlyWeatherSummaryAdmin(admin.ModelAdmin):
    list_display = ('year_month', 'min_temp_f', 'max_temp_f', 'avg_temp_f', 
                   'total_rainfall_inches', 'rainy_days')
    readonly_fields = ('min_temp_f', 'max_temp_f', 'avg_temp_f', 'total_rainfall_inches')
