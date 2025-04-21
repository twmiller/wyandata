from django.shortcuts import render
from django.http import JsonResponse
from .models import OutdoorWeatherReading, IndoorSensor
from django.views.decorators.csrf import csrf_exempt
import json
from datetime import datetime
from django.utils import timezone
import pytz

def weather_dashboard(request):
    """View to display the latest weather data"""
    outdoor_reading = OutdoorWeatherReading.objects.order_by('-time').first()
    indoor_readings = IndoorSensor.objects.order_by('-time')[:5]
    
    context = {
        'outdoor_reading': outdoor_reading,
        'indoor_readings': indoor_readings,
    }
    return render(request, 'weather/dashboard.html', context)

@csrf_exempt
def receive_weather_data(request):
    """API endpoint to receive weather data from rtl_433"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            # Extract common fields
            time_str = data.get('time')
            
            # Parse naive datetime and make it timezone-aware (Mountain Time)
            naive_time = datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')
            
            # Use Mountain Time timezone - you can change to 'US/Mountain', 'MST', 'MDT' as appropriate
            mountain_tz = pytz.timezone('America/Denver')
            aware_time = mountain_tz.localize(naive_time)
            
            # Convert to the project's timezone if different (as defined in settings.py)
            time = timezone.localtime(aware_time)
            
            model = data.get('model')
            sensor_id = data.get('id')
            battery_ok = bool(data.get('battery_ok', 1))
            temperature_c = data.get('temperature_C')
            humidity = data.get('humidity')
            
            # Process based on model type
            if 'WH24' in model or 'WH65' in model:
                # Create outdoor weather reading
                reading = OutdoorWeatherReading(
                    time=time,
                    model=model,
                    sensor_id=sensor_id,
                    battery_ok=battery_ok,
                    temperature_C=temperature_c,
                    humidity=humidity,
                    wind_dir_deg=data.get('wind_dir_deg'),
                    wind_avg_m_s=data.get('wind_avg_m_s'),
                    wind_max_m_s=data.get('wind_max_m_s'),
                    rain_mm=data.get('rain_mm'),
                    uv=data.get('uv'),
                    uvi=data.get('uvi'),
                    light_lux=data.get('light_lux'),
                    mic=data.get('mic')
                )
                reading.save()
                
            elif 'WN32P' in model:
                # Create indoor sensor reading
                reading = IndoorSensor(
                    time=time,
                    model=model,
                    sensor_id=sensor_id,
                    battery_ok=battery_ok,
                    temperature_C=temperature_c,
                    humidity=humidity,
                    channel=data.get('channel'),
                    mic=data.get('mic')
                )
                reading.save()
                
            return JsonResponse({'status': 'success'})
            
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
            
    return JsonResponse({'status': 'error', 'message': 'Only POST requests are allowed'}, status=405)
