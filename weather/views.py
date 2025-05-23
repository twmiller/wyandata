import logging
from django.shortcuts import render
from django.http import JsonResponse
from .models import OutdoorWeatherReading, IndoorSensor, DailyWeatherSummary, MonthlyWeatherSummary
from django.views.decorators.csrf import csrf_exempt
import json
from datetime import datetime, timedelta, date
from django.utils import timezone
import pytz
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

# Get a logger for this module
logger = logging.getLogger(__name__)

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
            logger.info("Weather data received from rtl_433")
            data = json.loads(request.body)
            logger.debug(f"Received data: {data}")
            
            # Extract common fields
            time_str = data.get('time')
            if not time_str:
                logger.error("Missing 'time' field in weather data")
                return JsonResponse({'status': 'error', 'message': "Missing 'time' field"}, status=400)
            
            try:
                # Parse naive datetime and make it timezone-aware (Mountain Time)
                naive_time = datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')
                
                # Use Mountain Time timezone
                mountain_tz = pytz.timezone('America/Denver')
                aware_time = mountain_tz.localize(naive_time)
                
                # Convert to the project's timezone if different (as defined in settings.py)
                time = timezone.localtime(aware_time)
            except Exception as e:
                logger.error(f"Error parsing datetime: {e}")
                return JsonResponse({'status': 'error', 'message': f"Invalid datetime format: {str(e)}"}, status=400)
            
            model = data.get('model')
            sensor_id = data.get('id')
            battery_ok = bool(data.get('battery_ok', 1))
            temperature_c = data.get('temperature_C')
            temperature_f = data.get('temperature_F')  # Get source temperature_F
            humidity = data.get('humidity')
            location = data.get('location')  # Get source location
            
            # Process based on model type
            if 'WH24' in model or 'WH65' in model:
                # Create outdoor weather reading
                reading = OutdoorWeatherReading(
                    time=time,
                    model=model,
                    sensor_id=sensor_id,
                    battery_ok=battery_ok,
                    temperature_C=temperature_c,
                    temperature_F=temperature_f,  # Store provided temperature_F
                    humidity=humidity,
                    location=location,  # Store provided location
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
                
                # Send update to WebSocket
                channel_layer = get_channel_layer()
                
                # Check if we have an indoor sensor reading
                indoor_reading = IndoorSensor.objects.order_by('-time').first()
                
                # Prepare WebSocket data
                ws_data = {
                    "timestamp": reading.time.isoformat(),
                    "outdoor": {
                        "model": reading.model,
                        "sensor_id": reading.sensor_id,
                        "location": reading.location,  # Include source location
                        "temperature": {
                            "celsius": reading.temperature_C,
                            "fahrenheit": reading.temperature_F or reading.calculated_temperature_F  # Use provided F if available
                        },
                        "humidity": reading.humidity,
                        "wind": {
                            "direction_degrees": reading.wind_dir_deg,
                            "direction_cardinal": reading.wind_direction_cardinal,
                            "speed": {
                                "avg_m_s": reading.wind_avg_m_s,
                                "avg_mph": reading.wind_avg_mph,
                                "max_m_s": reading.wind_max_m_s,
                                "max_mph": reading.wind_max_mph
                            }
                        },
                        "rain": {
                            "counter": {
                                "total_mm": reading.rain_mm,
                                "total_inches": reading.rain_inches,
                                "description": "Cumulative rainfall counter since station installation or last reset"
                            },
                            "recent": {
                                "since_previous_reading_inches": reading.rainfall_since_previous,
                                "last_hour_inches": reading.get_rainfall_since(hours=1),
                                "last_24h_inches": reading.get_rainfall_since(hours=24),
                                "description": "Rainfall measured over recent time periods"
                            }
                        }
                    }
                }
                
                # Add UV and light data if available
                if reading.uv is not None:
                    ws_data['outdoor']['uv'] = reading.uv
                
                if reading.uvi is not None:
                    ws_data['outdoor']['uvi'] = reading.uvi
                    
                if reading.light_lux is not None:
                    ws_data['outdoor']['light_lux'] = reading.light_lux
                
                # Add indoor data if available
                if indoor_reading:
                    ws_data['indoor'] = {
                        "model": indoor_reading.model,
                        "sensor_id": indoor_reading.sensor_id,
                        "location": indoor_reading.location,  # Include source location
                        "temperature": {
                            "celsius": indoor_reading.temperature_C,
                            "fahrenheit": indoor_reading.temperature_F or indoor_reading.calculated_temperature_F  # Use provided F if available
                        },
                        "humidity": indoor_reading.humidity,
                        "timestamp": indoor_reading.time.isoformat()
                    }
                
                async_to_sync(channel_layer.group_send)(
                    "weather_data",
                    {
                        "type": "weather_update",
                        "data": ws_data
                    }
                )
                
            elif 'WN32P' in model or 'WH32B' in model or 'WH31B' in model or 'AmbientWeather-WH31B' in model:
                # Create indoor sensor reading
                reading = IndoorSensor(
                    time=time,
                    model=model,
                    sensor_id=sensor_id,
                    battery_ok=battery_ok,
                    temperature_C=temperature_c,
                    temperature_F=temperature_f,  # Store provided temperature_F
                    humidity=humidity,
                    location=location,  # Store provided location
                    channel=data.get('channel'),
                    pressure_hPa=data.get('pressure_hPa'),
                    mic=data.get('mic')
                )
                
                # Set location for specific indoor sensors if no location was provided
                if not location and ('WH31B' in model or 'AmbientWeather-WH31B' in model):
                    # Map sensor_id and channel to location
                    if sensor_id == 238 and data.get('channel') == 1:
                        reading.location = "First location"
                    elif sensor_id == 232 and data.get('channel') == 3:
                        reading.location = "Garden Shed"
                
                reading.save()
                
                # Get the latest outdoor reading
                outdoor_reading = OutdoorWeatherReading.objects.order_by('-time').first()
                
                # Only send WebSocket update if we have both indoor and outdoor readings
                if outdoor_reading:
                    channel_layer = get_channel_layer()
                    
                    # Prepare WebSocket data
                    ws_data = {
                        "timestamp": outdoor_reading.time.isoformat(),
                        "outdoor": {
                            "model": outdoor_reading.model,
                            "sensor_id": outdoor_reading.sensor_id,
                            "location": outdoor_reading.location,  # Include source location
                            "temperature": {
                                "celsius": outdoor_reading.temperature_C,
                                "fahrenheit": outdoor_reading.temperature_F or outdoor_reading.calculated_temperature_F  # Use provided F if available
                            },
                            "humidity": outdoor_reading.humidity,
                            "wind": {
                                "direction_degrees": outdoor_reading.wind_dir_deg,
                                "direction_cardinal": outdoor_reading.wind_direction_cardinal,
                                "speed": {
                                    "avg_m_s": outdoor_reading.wind_avg_m_s,
                                    "avg_mph": outdoor_reading.wind_avg_mph,
                                    "max_m_s": outdoor_reading.wind_max_m_s,
                                    "max_mph": outdoor_reading.wind_max_mph
                                }
                            },
                            "rain": {
                                "counter": {
                                    "total_mm": outdoor_reading.rain_mm,
                                    "total_inches": outdoor_reading.rain_inches,
                                    "description": "Cumulative rainfall counter since station installation or last reset"
                                },
                                "recent": {
                                    "since_previous_reading_inches": outdoor_reading.rainfall_since_previous,
                                    "last_hour_inches": outdoor_reading.get_rainfall_since(hours=1),
                                    "last_24h_inches": outdoor_reading.get_rainfall_since(hours=24),
                                    "description": "Rainfall measured over recent time periods"
                                }
                            }
                        },
                        "indoor": {
                            "model": reading.model,
                            "sensor_id": reading.sensor_id,
                            "location": reading.location,  # Include source location
                            "temperature": {
                                "celsius": reading.temperature_C,
                                "fahrenheit": reading.temperature_F or reading.calculated_temperature_F  # Use provided F if available
                            },
                            "humidity": reading.humidity,
                            "timestamp": reading.time.isoformat()
                        }
                    }
                    
                    # Add UV and light data if available
                    if outdoor_reading.uv is not None:
                        ws_data['outdoor']['uv'] = outdoor_reading.uv
                    
                    if outdoor_reading.uvi is not None:
                        ws_data['outdoor']['uvi'] = outdoor_reading.uvi
                        
                    if outdoor_reading.light_lux is not None:
                        ws_data['outdoor']['light_lux'] = outdoor_reading.light_lux
                    
                    # Add pressure data to the indoor reading in the websocket data
                    if reading.pressure_hPa is not None:
                        ws_data['indoor']['pressure'] = {
                            'hPa': reading.pressure_hPa,
                            'inHg': reading.pressure_inHg
                        }
                    
                    async_to_sync(channel_layer.group_send)(
                        "weather_data",
                        {
                            "type": "weather_update",
                            "data": ws_data
                        }
                    )
                    
            return JsonResponse({'status': 'success'})
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON: {e}")
            return JsonResponse({'status': 'error', 'message': f"Invalid JSON: {str(e)}"}, status=400)
        except Exception as e:
            logger.error(f"Error processing weather data: {e}")
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
            
    return JsonResponse({'status': 'error', 'message': 'Only POST requests are allowed'}, status=405)

def get_current_weather(request):
    """API endpoint to get the current weather data"""
    try:
        # Get the latest outdoor reading
        outdoor_reading = OutdoorWeatherReading.objects.order_by('-time').first()
        if not outdoor_reading:
            return JsonResponse({'status': 'error', 'message': 'No outdoor weather data available'}, status=404)
        
        # Format the response data
        data = {
            'status': 'success',
            'timestamp': outdoor_reading.time.isoformat(),
            'outdoor': {
                'model': outdoor_reading.model,
                'sensor_id': outdoor_reading.sensor_id,
                'location': outdoor_reading.location,
                'temperature': {
                    'celsius': outdoor_reading.temperature_C,
                    'fahrenheit': outdoor_reading.temperature_F or outdoor_reading.calculated_temperature_F
                },
                'humidity': outdoor_reading.humidity,
                'wind': {
                    'direction_degrees': outdoor_reading.wind_dir_deg,
                    'direction_cardinal': outdoor_reading.wind_direction_cardinal,
                    'speed': {
                        'avg_m_s': outdoor_reading.wind_avg_m_s,
                        'avg_mph': outdoor_reading.wind_avg_mph,
                        'max_m_s': outdoor_reading.wind_max_m_s,
                        'max_mph': outdoor_reading.wind_max_mph
                    }
                },
                'rain': {
                    'counter': {
                        'total_mm': outdoor_reading.rain_mm,
                        'total_inches': outdoor_reading.rain_inches,
                        'description': 'Cumulative rainfall counter since station installation or last reset'
                    },
                    'recent': {
                        'since_previous_reading_inches': outdoor_reading.rainfall_since_previous,
                        'last_hour_inches': outdoor_reading.get_rainfall_since(hours=1),
                        'last_24h_inches': outdoor_reading.get_rainfall_since(hours=24),
                        'description': 'Rainfall measured over recent time periods'
                    }
                }
            }
        }
        
        # Add UV and light data if available
        if outdoor_reading.uv is not None:
            data['outdoor']['uv'] = outdoor_reading.uv
        
        if outdoor_reading.uvi is not None:
            data['outdoor']['uvi'] = outdoor_reading.uvi
        
        if outdoor_reading.light_lux is not None:
            data['outdoor']['light_lux'] = outdoor_reading.light_lux
        
        # Get all indoor sensors (latest reading from each unique sensor/channel combination)
        indoor_sensors_data = []
        
        # Track sensor_id/channel combinations we've seen
        seen_sensors = set()
        
        # Get all indoor sensors ordered by time (newest first)
        for sensor in IndoorSensor.objects.order_by('-time'):
            # Create a unique key for this sensor based on sensor_id and channel
            sensor_key = f"{sensor.sensor_id}_{sensor.channel}"
            
            # Only include the first (most recent) reading from each unique sensor
            if sensor_key not in seen_sensors:
                seen_sensors.add(sensor_key)
                
                # Create sensor data dictionary
                sensor_data = {
                    'model': sensor.model,
                    'sensor_id': sensor.sensor_id,
                    'channel': sensor.channel,
                    'location': sensor.location,
                    'temperature': {
                        'celsius': sensor.temperature_C,
                        'fahrenheit': sensor.temperature_F or sensor.calculated_temperature_F
                    },
                    'humidity': sensor.humidity,
                    'timestamp': sensor.time.isoformat()
                }
                
                # Add pressure data if available
                if hasattr(sensor, 'pressure_hPa') and sensor.pressure_hPa is not None:
                    sensor_data['pressure'] = {
                        'hPa': sensor.pressure_hPa,
                        'inHg': sensor.pressure_inHg
                    }
                
                indoor_sensors_data.append(sensor_data)
        
        # Add all indoor sensors to the response
        data['indoor_sensors'] = indoor_sensors_data
        
        return JsonResponse(data)
        
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

def get_daily_weather(request):
    """API endpoint to get daily weather summaries"""
    try:
        # Get query parameters
        days = int(request.GET.get('days', 7))  # Default to 7 days
        days = min(days, 365)  # Limit to reasonable amount
        
        # Calculate date range
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days-1)
        
        # Get daily summaries in the date range
        daily_summaries = DailyWeatherSummary.objects.filter(
            date__range=[start_date, end_date]
        ).order_by('date')
        
        # Format the response data
        results = []
        for summary in daily_summaries:
            results.append({
                'date': summary.date.isoformat(),
                'temperature': {
                    'min_c': summary.min_temp_c,
                    'max_c': summary.max_temp_c,
                    'avg_c': summary.avg_temp_c,
                    'min_f': summary.min_temp_f,
                    'max_f': summary.max_temp_f,
                    'avg_f': summary.avg_temp_f
                },
                'humidity': {
                    'min': summary.min_humidity,
                    'max': summary.max_humidity,
                    'avg': summary.avg_humidity
                },
                'rainfall': {
                    'total_mm': summary.total_rainfall_mm,
                    'total_inches': summary.total_rainfall_inches
                },
                'wind': {
                    'max_speed_mph': summary.max_wind_speed_mph,
                    'predominant_direction': summary.predominant_wind_direction
                },
                'max_uvi': summary.max_uvi
            })
        
        return JsonResponse({'status': 'success', 'days': len(results), 'summaries': results})
        
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

def get_monthly_weather(request):
    """API endpoint to get monthly weather summaries"""
    try:
        # Get query parameters
        months = int(request.GET.get('months', 12))  # Default to 12 months
        months = min(months, 60)  # Limit to reasonable amount
        
        # Calculate date range
        today = timezone.now().date()
        end_month = today.strftime('%Y-%m')
        
        # Get earliest possible year-month
        earliest_date = today.replace(day=1) - timedelta(days=30*months)
        start_month = earliest_date.strftime('%Y-%m')
        
        # Get monthly summaries
        monthly_summaries = MonthlyWeatherSummary.objects.filter(
            year_month__gte=start_month,
            year_month__lte=end_month
        ).order_by('year_month')
        
        # Format the response data
        results = []
        for summary in monthly_summaries:
            results.append({
                'year_month': summary.year_month,
                'temperature': {
                    'min_c': summary.min_temp_c,
                    'max_c': summary.max_temp_c,
                    'avg_c': summary.avg_temp_c,
                    'min_f': summary.min_temp_f,
                    'max_f': summary.max_temp_f,
                    'avg_f': summary.avg_temp_f
                },
                'rainfall': {
                    'total_mm': summary.total_rainfall_mm,
                    'total_inches': summary.total_rainfall_inches,
                    'rainy_days': summary.rainy_days
                },
                'max_wind_speed_mph': summary.max_wind_speed_mph
            })
        
        return JsonResponse({'status': 'success', 'months': len(results), 'summaries': results})
        
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

def get_recent_readings(request):
    """API endpoint to get a specified number of recent weather readings"""
    try:
        # Get query parameters
        count = int(request.GET.get('count', 100))  # Default to 100 readings
        count = min(count, 1000)  # Limit to reasonable amount
        
        # Get sensor_id if specified to filter by a specific sensor
        sensor_id = request.GET.get('sensor_id', None)
        
        # Get most recent readings
        query = OutdoorWeatherReading.objects.order_by('-time')
        
        # Filter by sensor_id if provided
        if sensor_id:
            try:
                sensor_id = int(sensor_id)
                query = query.filter(sensor_id=sensor_id)
            except ValueError:
                return JsonResponse({'status': 'error', 'message': 'Invalid sensor_id'}, status=400)
        
        # Get all readings first to calculate time range before slicing
        if query.exists():
            start_time = query.order_by('time').first().time
            end_time = query.order_by('-time').first().time
            
            # Now get the sliced readings
            readings = query[:count]
            
            # Format the response data
            results = []
            for reading in readings:
                results.append({
                    'timestamp': reading.time.isoformat(),
                    'model': reading.model,
                    'sensor_id': reading.sensor_id,
                    'location': reading.location,  # Include source location
                    'temperature': {
                        'celsius': reading.temperature_C,
                        'fahrenheit': reading.temperature_F or reading.calculated_temperature_F  # Use provided F if available
                    },
                    'humidity': reading.humidity,
                    'wind': {
                        'direction_degrees': reading.wind_dir_deg,
                        'direction_cardinal': reading.wind_direction_cardinal,
                        'speed': {
                            'avg_m_s': reading.wind_avg_m_s,
                            'avg_mph': reading.wind_avg_mph,
                            'max_m_s': reading.wind_max_m_s,
                            'max_mph': reading.wind_max_mph
                        }
                    },
                    'rain': {
                        "counter": {
                            "total_mm": reading.rain_mm,
                            "total_inches": reading.rain_inches,
                            "description": "Cumulative rainfall counter since station installation or last reset"
                        },
                        "recent": {
                            "since_previous_reading_inches": reading.rainfall_since_previous,
                            "last_hour_inches": reading.get_rainfall_since(hours=1),
                            "last_24h_inches": reading.get_rainfall_since(hours=24),
                            "description": "Rainfall measured over recent time periods"
                        }
                    },
                    'uv': reading.uv,
                    'uvi': reading.uvi,
                    'light_lux': reading.light_lux
                })
            
            # Include time interval information
            time_info = {}
            if len(readings) >= 2:
                duration = end_time - start_time
                time_info = {
                    'start_time': start_time.isoformat(),
                    'end_time': end_time.isoformat(),
                    'duration_seconds': duration.total_seconds(),
                    'duration_minutes': duration.total_seconds() / 60,
                    'duration_hours': duration.total_seconds() / 3600
                }
            
            return JsonResponse({
                'status': 'success',
                'count': len(results),
                'time_info': time_info,
                'readings': results
            })
        
        else:
            return JsonResponse({
                'status': 'success',
                'count': 0,
                'time_info': {},
                'readings': []
            })
        
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
