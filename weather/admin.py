from django.contrib import admin
from .models import OutdoorWeatherReading, IndoorSensor

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
    list_display = ('time', 'model', 'sensor_id', 'temperature_F', 'humidity', 'battery_ok')
    list_filter = ('model', 'sensor_id')
    date_hierarchy = 'time'
    search_fields = ('model', 'sensor_id')
    readonly_fields = ('temperature_F',)
