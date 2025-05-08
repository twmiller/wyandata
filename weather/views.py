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
            
            try:# Use Mountain Time timezone - you can change to 'US/Mountain', 'MST', 'MDT' as appropriate
                # Parse naive datetime and make it timezone-aware (Mountain Time)ne('America/Denver')
                naive_time = datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')ocalize(naive_time)
                
                # Use Mountain Time timezonefferent (as defined in settings.py)
                mountain_tz = pytz.timezone('America/Denver')
                aware_time = mountain_tz.localize(naive_time)
                
                # Convert to the project's timezone if different (as defined in settings.py)sensor_id = data.get('id')
                time = timezone.localtime(aware_time)attery_ok', 1))
            except Exception as e:C')
                logger.error(f"Error parsing datetime: {e}")e_F')  # Get source temperature_F
                return JsonResponse({'status': 'error', 'message': f"Invalid datetime format: {str(e)}"}, status=400)
            t('location')  # Get source location
            model = data.get('model')
            sensor_id = data.get('id')e
            battery_ok = bool(data.get('battery_ok', 1))n model:
            temperature_c = data.get('temperature_C')
            temperature_f = data.get('temperature_F')  # Get source temperature_F
            humidity = data.get('humidity')
            location = data.get('location')  # Get source location
            
            # Process based on model type
            if 'WH24' in model or 'WH65' in model:
                # Create outdoor weather reading  # Store provided temperature_F
                reading = OutdoorWeatherReading(
                    time=time,# Store provided location
                    model=model,deg'),
                    sensor_id=sensor_id,et('wind_avg_m_s'),
                    battery_ok=battery_ok,   wind_max_m_s=data.get('wind_max_m_s'),
                    temperature_C=temperature_c,ta.get('rain_mm'),
                    temperature_F=temperature_f,  # Store provided temperature_F    uv=data.get('uv'),
                    humidity=humidity,
                    location=location,  # Store provided location,
                    wind_dir_deg=data.get('wind_dir_deg'),    mic=data.get('mic')
                    wind_avg_m_s=data.get('wind_avg_m_s'),
                    wind_max_m_s=data.get('wind_max_m_s'),
                    rain_mm=data.get('rain_mm'),
                    uv=data.get('uv'),et
                    uvi=data.get('uvi'),er = get_channel_layer()
                    light_lux=data.get('light_lux'),
                    mic=data.get('mic')ve an indoor sensor reading
                )bjects.order_by('-time').first()
                reading.save()
                
                # Send update to WebSocket
                channel_layer = get_channel_layer()
                
                # Check if we have an indoor sensor readingodel": reading.model,
                indoor_reading = IndoorSensor.objects.order_by('-time').first()d,
                ": reading.location,  # Include source location
                # Prepare WebSocket data
                ws_data = {
                    "timestamp": reading.time.isoformat(),t": reading.temperature_F or reading.calculated_temperature_F  # Use provided F if available
                    "outdoor": {
                        "model": reading.model,
                        "sensor_id": reading.sensor_id,
                        "location": reading.location,  # Include source locationir_deg,
                        "temperature": {direction_cardinal": reading.wind_direction_cardinal,
                            "celsius": reading.temperature_C,  "speed": {
                            "fahrenheit": reading.temperature_F or reading.calculated_temperature_F  # Use provided F if availableavg_m_s": reading.wind_avg_m_s,
                        },": reading.wind_avg_mph,
                        "humidity": reading.humidity,m_s,
                        "wind": {
                            "direction_degrees": reading.wind_dir_deg,
                            "direction_cardinal": reading.wind_direction_cardinal,
                            "speed": {
                                "avg_m_s": reading.wind_avg_m_s,
                                "avg_mph": reading.wind_avg_mph,
                                "max_m_s": reading.wind_max_m_s,
                                "max_mph": reading.wind_max_mphnstallation or last reset"
                            },
                        },   "recent": {
                        "rain": {           "since_previous_reading_inches": reading.rainfall_since_previous,
                            "counter": {               "last_hour_inches": reading.get_rainfall_since(hours=1),
                                "total_mm": reading.rain_mm,                "last_24h_inches": reading.get_rainfall_since(hours=24),
                                "total_inches": reading.rain_inches,fall measured over recent time periods"
                                "description": "Cumulative rainfall counter since station installation or last reset"
                            },
                            "recent": {    }
                                "since_previous_reading_inches": reading.rainfall_since_previous,
                                "last_hour_inches": reading.get_rainfall_since(hours=1),
                                "last_24h_inches": reading.get_rainfall_since(hours=24),d UV and light data if available
                                "description": "Rainfall measured over recent time periods"
                            }
                        }
                    }
                }or']['uvi'] = reading.uvi
                
                # Add UV and light data if available
                if reading.uv is not None:light_lux
                    ws_data['outdoor']['uv'] = reading.uv
                ilable
                if reading.uvi is not None:
                    ws_data['outdoor']['uvi'] = reading.uvi
                    odel": indoor_reading.model,
                if reading.light_lux is not None:d,
                    ws_data['outdoor']['light_lux'] = reading.light_luxude source location
                   "temperature": {
                # Add indoor data if available            "celsius": indoor_reading.temperature_C,
                if indoor_reading:.temperature_F or indoor_reading.calculated_temperature_F  # Use provided F if available
                    ws_data['indoor'] = {
                        "model": indoor_reading.model,   "humidity": indoor_reading.humidity,
                        "sensor_id": indoor_reading.sensor_id,ng.time.isoformat()
                        "location": indoor_reading.location,  # Include source location
                        "temperature": {
                            "celsius": indoor_reading.temperature_C,sync_to_sync(channel_layer.group_send)(
                            "fahrenheit": indoor_reading.temperature_F or indoor_reading.calculated_temperature_F  # Use provided F if available    "weather_data",
                        },
                        "humidity": indoor_reading.humidity,e",
                        "timestamp": indoor_reading.time.isoformat()
                    }
                
                async_to_sync(channel_layer.group_send)(
                    "weather_data",B' in model or 'WH31B' in model or 'AmbientWeather-WH31B' in model:
                    {
                        "type": "weather_update",
                        "data": ws_data
                    }
                )
                
            elif 'WN32P' in model or 'WH32B' in model or 'WH31B' in model or 'AmbientWeather-WH31B' in model:rature_c,
                # Create indoor sensor reading   temperature_F=temperature_f,  # Store provided temperature_F
                reading = IndoorSensor(    humidity=humidity,
                    time=time,
                    model=model,
                    sensor_id=sensor_id,
                    battery_ok=battery_ok,
                    temperature_C=temperature_c,
                    temperature_F=temperature_f,  # Store provided temperature_F
                    humidity=humidity,rs if no location was provided
                    location=location,  # Store provided locationif not location and ('WH31B' in model or 'AmbientWeather-WH31B' in model):
                    channel=data.get('channel'),or_id and channel to location
                    pressure_hPa=data.get('pressure_hPa'),    if sensor_id == 238 and data.get('channel') == 1:
                    mic=data.get('mic')t location"
                )
                        reading.location = "Garden Shed"
                # Set location for specific indoor sensors if no location was provided
                if not location and ('WH31B' in model or 'AmbientWeather-WH31B' in model):
                    # Map sensor_id and channel to location
                    if sensor_id == 238 and data.get('channel') == 1:t the latest outdoor reading
                        reading.location = "First location"therReading.objects.order_by('-time').first()
                    elif sensor_id == 232 and data.get('channel') == 3:
                        reading.location = "Garden Shed"d outdoor readings
                
                reading.save()
                
                # Get the latest outdoor reading
                outdoor_reading = OutdoorWeatherReading.objects.order_by('-time').first()
                
                # Only send WebSocket update if we have both indoor and outdoor readings
                if outdoor_reading:odel": outdoor_reading.model,
                    channel_layer = get_channel_layer()d,
                    ": outdoor_reading.location,  # Include source location
                    # Prepare WebSocket data
                    ws_data = {
                        "timestamp": outdoor_reading.time.isoformat(),t": outdoor_reading.temperature_F or outdoor_reading.calculated_temperature_F  # Use provided F if available
                        "outdoor": {
                            "model": outdoor_reading.model,
                            "sensor_id": outdoor_reading.sensor_id,
                            "location": outdoor_reading.location,  # Include source locationir_deg,
                            "temperature": {direction_cardinal": outdoor_reading.wind_direction_cardinal,
                                "celsius": outdoor_reading.temperature_C,  "speed": {
                                "fahrenheit": outdoor_reading.temperature_F or outdoor_reading.calculated_temperature_F  # Use provided F if availableavg_m_s": outdoor_reading.wind_avg_m_s,
                            },": outdoor_reading.wind_avg_mph,
                            "humidity": outdoor_reading.humidity,m_s,
                            "wind": {
                                "direction_degrees": outdoor_reading.wind_dir_deg,
                                "direction_cardinal": outdoor_reading.wind_direction_cardinal,
                                "speed": {
                                    "avg_m_s": outdoor_reading.wind_avg_m_s,
                                    "avg_mph": outdoor_reading.wind_avg_mph,
                                    "max_m_s": outdoor_reading.wind_max_m_s,
                                    "max_mph": outdoor_reading.wind_max_mphnstallation or last reset"
                                },
                            },   "recent": {
                            "rain": {          "since_previous_reading_inches": outdoor_reading.rainfall_since_previous,
                                "counter": { "last_hour_inches": outdoor_reading.get_rainfall_since(hours=1),
                                    "total_mm": outdoor_reading.rain_mm,s": outdoor_reading.get_rainfall_since(hours=24),
                                    "total_inches": outdoor_reading.rain_inches,l measured over recent time periods"
                                    "description": "Cumulative rainfall counter since station installation or last reset"
                                },
                                "recent": {
                                    "since_previous_reading_inches": outdoor_reading.rainfall_since_previous,
                                    "last_hour_inches": outdoor_reading.get_rainfall_since(hours=1),odel": reading.model,
                                    "last_24h_inches": outdoor_reading.get_rainfall_since(hours=24),d,
                                    "description": "Rainfall measured over recent time periods"ude source location
                                }   "temperature": {
                            }           "celsius": reading.temperature_C,
                        },            "fahrenheit": reading.temperature_F or reading.calculated_temperature_F  # Use provided F if available
                        "indoor": {
                            "model": reading.model,ty,
                            "sensor_id": reading.sensor_id,
                            "location": reading.location,  # Include source location    }
                            "temperature": {
                                "celsius": reading.temperature_C,
                                "fahrenheit": reading.temperature_F or reading.calculated_temperature_F  # Use provided F if availabled UV and light data if available
                            },
                            "humidity": reading.humidity,
                            "timestamp": reading.time.isoformat()
                        }
                    }oor_reading.uvi
                    
                    # Add UV and light data if availableNone:
                    if outdoor_reading.uv is not None: outdoor_reading.light_lux
                        ws_data['outdoor']['uv'] = outdoor_reading.uv
                    # Add pressure data to the indoor reading in the websocket data
                    if outdoor_reading.uvi is not None:
                        ws_data['outdoor']['uvi'] = outdoor_reading.uvi']['pressure'] = {
                           'hPa': reading.pressure_hPa,
                    if outdoor_reading.light_lux is not None:inHg
                        ws_data['outdoor']['light_lux'] = outdoor_reading.light_lux
                    
                    # Add pressure data to the indoor reading in the websocket datasync_to_sync(channel_layer.group_send)(
                    if reading.pressure_hPa is not None:    "weather_data",
                        ws_data['indoor']['pressure'] = {
                            'hPa': reading.pressure_hPa,                "type": "weather_update",
                            'inHg': reading.pressure_inHgata": ws_data
                        }
                            )
                    async_to_sync(channel_layer.group_send)(
                        "weather_data",            return JsonResponse({'status': 'success'})
                        {
                            "type": "weather_update",
                            "data": ws_data    return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
                        }
                    )lowed'}, status=405)
                    
            return JsonResponse({'status': 'success'})):
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON: {e}")eading
            return JsonResponse({'status': 'error', 'message': f"Invalid JSON: {str(e)}"}, status=400)reading = OutdoorWeatherReading.objects.order_by('-time').first()
        except Exception as e:
            logger.error(f"Error processing weather data: {e}")
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)esponse({'status': 'error', 'message': 'No outdoor weather data available'}, status=404)
            
    return JsonResponse({'status': 'error', 'message': 'Only POST requests are allowed'}, status=405)

def get_current_weather(request):
    """API endpoint to get the current weather data"""
    try:
        # Get the latest outdoor readingodel': outdoor_reading.model,
        outdoor_reading = OutdoorWeatherReading.objects.order_by('-time').first()d,
        ': outdoor_reading.location,
        if not outdoor_reading:
            return JsonResponse({'status': 'error', 'message': 'No outdoor weather data available'}, status=404)
        t': outdoor_reading.temperature_F or outdoor_reading.calculated_temperature_F
        # Format the response data
        data = {
            'status': 'success',
            'timestamp': outdoor_reading.time.isoformat(),ir_deg,
            'outdoor': {direction_cardinal': outdoor_reading.wind_direction_cardinal,
                'model': outdoor_reading.model,  'speed': {
                'sensor_id': outdoor_reading.sensor_id,avg_m_s': outdoor_reading.wind_avg_m_s,
                'location': outdoor_reading.location,': outdoor_reading.wind_avg_mph,
                'temperature': {m_s,
                    'celsius': outdoor_reading.temperature_C,
                    'fahrenheit': outdoor_reading.temperature_F or outdoor_reading.calculated_temperature_F
                },
                'humidity': outdoor_reading.humidity,
                'wind': {
                    'direction_degrees': outdoor_reading.wind_dir_deg,
                    'direction_cardinal': outdoor_reading.wind_direction_cardinal,
                    'speed': {nstallation or last reset'
                        'avg_m_s': outdoor_reading.wind_avg_m_s,,
                        'avg_mph': outdoor_reading.wind_avg_mph,   'recent': {
                        'max_m_s': outdoor_reading.wind_max_m_s,           'since_previous_reading_inches': outdoor_reading.rainfall_since_previous,
                        'max_mph': outdoor_reading.wind_max_mph               'last_hour_inches': outdoor_reading.get_rainfall_since(hours=1),
                    }                'last_24h_inches': outdoor_reading.get_rainfall_since(hours=24),
                },fall measured over recent time periods'
                'rain': {
                    'counter': {
                        'total_mm': outdoor_reading.rain_mm,    }
                        'total_inches': outdoor_reading.rain_inches,
                        'description': 'Cumulative rainfall counter since station installation or last reset'
                    },d UV and light data if available
                    'recent': {
                        'since_previous_reading_inches': outdoor_reading.rainfall_since_previous,
                        'last_hour_inches': outdoor_reading.get_rainfall_since(hours=1),
                        'last_24h_inches': outdoor_reading.get_rainfall_since(hours=24),
                        'description': 'Rainfall measured over recent time periods''] = outdoor_reading.uvi
                    }    
                }
            }'light_lux'] = outdoor_reading.light_lux
        }
        ue sensor/channel combination)
        # Add UV and light data if available
        if outdoor_reading.uv is not None:
            data['outdoor']['uv'] = outdoor_reading.uv
        _sensors = set()
        if outdoor_reading.uvi is not None:
            data['outdoor']['uvi'] = outdoor_reading.uvime (newest first)
            rder_by('-time'):
        if outdoor_reading.light_lux is not None:eate a unique key for this sensor based on sensor_id and channel
            data['outdoor']['light_lux'] = outdoor_reading.light_luxsensor.channel}"
        
        # Get all indoor sensors (latest reading from each unique sensor/channel combination) recent) reading from each unique sensor
        indoor_sensors_data = []
        
        # Track sensor_id/channel combinations we've seen
        seen_sensors = set() dictionary
        
        # Get all indoor sensors ordered by time (newest first)
        for sensor in IndoorSensor.objects.order_by('-time'):ensor_id': sensor.sensor_id,
            # Create a unique key for this sensor based on sensor_id and channel
            sensor_key = f"{sensor.sensor_id}_{sensor.channel}"
               'temperature': {
            # Only include the first (most recent) reading from each unique sensor        'celsius': sensor.temperature_C,
            if sensor_key not in seen_sensors:perature_F or sensor.calculated_temperature_F
                seen_sensors.add(sensor_key)
                ,
                # Create sensor data dictionarymat()
                sensor_data = {
                    'model': sensor.model,
                    'sensor_id': sensor.sensor_id,# Add pressure data if available
                    'channel': sensor.channel,sensor.pressure_hPa is not None:
                    'location': sensor.location,            sensor_data['pressure'] = {
                    'temperature': {Pa,
                        'celsius': sensor.temperature_C,
                        'fahrenheit': sensor.temperature_F or sensor.calculated_temperature_F            }
                    },
                    'humidity': sensor.humidity,        indoor_sensors_data.append(sensor_data)
                    'timestamp': sensor.time.isoformat()
                }
                        data['indoor_sensors'] = indoor_sensors_data
                # Add pressure data if available
                if hasattr(sensor, 'pressure_hPa') and sensor.pressure_hPa is not None:
                    sensor_data['pressure'] = {
                        'hPa': sensor.pressure_hPa,
                        'inHg': sensor.pressure_inHg status=500)
                    }
                daily_weather(request):
                indoor_sensors_data.append(sensor_data)ly weather summaries"""
        
        # Add all indoor sensors to the response
        data['indoor_sensors'] = indoor_sensors_datadays = int(request.GET.get('days', 7))  # Default to 7 days
        nable amount
        return JsonResponse(data)
        
    except Exception as e:e.now().date()
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)start_date = end_date - timedelta(days=days-1)

def get_daily_weather(request):summaries in the date range
    """API endpoint to get daily weather summaries"""ummary.objects.filter(
    try:rt_date, end_date]
        # Get query parameters
        days = int(request.GET.get('days', 7))  # Default to 7 days
        days = min(days, 365)  # Limit to reasonable amount
        
        # Calculate date range
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days-1),
        
        # Get daily summaries in the date range  'min_c': summary.min_temp_c,
        daily_summaries = DailyWeatherSummary.objects.filter(summary.max_temp_c,
            date__range=[start_date, end_date]
        ).order_by('date')
        ,
        # Format the response data  'avg_f': summary.avg_temp_f
        results = []
        for summary in daily_summaries:
            results.append({
                'date': summary.date.isoformat(),  'max': summary.max_humidity,
                'temperature': {: summary.avg_humidity
                    'min_c': summary.min_temp_c,
                    'max_c': summary.max_temp_c,
                    'avg_c': summary.avg_temp_c,  'total_mm': summary.total_rainfall_mm,
                    'min_f': summary.min_temp_f,y.total_rainfall_inches
                    'max_f': summary.max_temp_f,  },
                    'avg_f': summary.avg_temp_f        'wind': {
                },
                'humidity': {            'predominant_direction': summary.predominant_wind_direction
                    'min': summary.min_humidity,
                    'max': summary.max_humidity,
                    'avg': summary.avg_humidity            })
                },
                'rainfall': {': len(results), 'summaries': results})
                    'total_mm': summary.total_rainfall_mm,
                    'total_inches': summary.total_rainfall_inches
                },500)
                'wind': {
                    'max_speed_mph': summary.max_wind_speed_mph,monthly_weather(request):
                    'predominant_direction': summary.predominant_wind_directionthly weather summaries"""
                },
                'max_uvi': summary.max_uvi
            })months = int(request.GET.get('months', 12))  # Default to 12 months
        to reasonable amount
        return JsonResponse({'status': 'success', 'days': len(results), 'summaries': results})
        
    except Exception as e:today = timezone.now().date()
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)ime('%Y-%m')

def get_monthly_weather(request):th
    """API endpoint to get monthly weather summaries"""(day=1) - timedelta(days=30*months)
    try:ate.strftime('%Y-%m')
        # Get query parameters
        months = int(request.GET.get('months', 12))  # Default to 12 months
        months = min(months, 60)  # Limit to reasonable amountaries = MonthlyWeatherSummary.objects.filter(
        
        # Calculate date rangeend_month
        today = timezone.now().date()
        end_month = today.strftime('%Y-%m')
        
        # Get earliest possible year-month
        earliest_date = today.replace(day=1) - timedelta(days=30*months)
        start_month = earliest_date.strftime('%Y-%m')
        ,
        # Get monthly summaries
        monthly_summaries = MonthlyWeatherSummary.objects.filter(  'min_c': summary.min_temp_c,
            year_month__gte=start_month,summary.max_temp_c,
            year_month__lte=end_month
        ).order_by('year_month')
        
        # Format the response data  'avg_f': summary.avg_temp_f
        results = []
        for summary in monthly_summaries:  'rainfall': {
            results.append({            'total_mm': summary.total_rainfall_mm,
                'year_month': summary.year_month,
                'temperature': {            'rainy_days': summary.rainy_days
                    'min_c': summary.min_temp_c,
                    'max_c': summary.max_temp_c,
                    'avg_c': summary.avg_temp_c,            })
                    'min_f': summary.min_temp_f,
                    'max_f': summary.max_temp_f,summaries': results})
                    'avg_f': summary.avg_temp_f
                },
                'rainfall': {0)
                    'total_mm': summary.total_rainfall_mm,
                    'total_inches': summary.total_rainfall_inches,recent_readings(request):
                    'rainy_days': summary.rainy_daysdings"""
                },
                'max_wind_speed_mph': summary.max_wind_speed_mph# Get query parameters
            })t('count', 100))  # Default to 100 readings
        
        return JsonResponse({'status': 'success', 'months': len(results), 'summaries': results})
        ilter by a specific sensor
    except Exception as e:equest.GET.get('sensor_id', None)
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

def get_recent_readings(request):time')
    """API endpoint to get a specified number of recent weather readings"""
    try:
        # Get query parametersif sensor_id:
        count = int(request.GET.get('count', 100))  # Default to 100 readings
        count = min(count, 1000)  # Limit to reasonable amount= int(sensor_id)
        
        # Get sensor_id if specified to filter by a specific sensor
        sensor_id = request.GET.get('sensor_id', None)    return JsonResponse({'status': 'error', 'message': 'Invalid sensor_id'}, status=400)
        
        # Get most recent readingscalculate time range before slicing
        query = OutdoorWeatherReading.objects.order_by('-time')uery.exists():
        y('time').first().time
        # Filter by sensor_id if provideduery.order_by('-time').first().time
        if sensor_id:
            try: readings
                sensor_id = int(sensor_id)
                query = query.filter(sensor_id=sensor_id)
            except ValueError:
                return JsonResponse({'status': 'error', 'message': 'Invalid sensor_id'}, status=400)
        
        # Get all readings first to calculate time range before slicing
        if query.exists():
            start_time = query.order_by('time').first().timeodel': reading.model,
            end_time = query.order_by('-time').first().timed,
            ': reading.location,  # Include source location
            # Now get the sliced readings
            readings = query[:count]
            t': reading.temperature_F or reading.calculated_temperature_F  # Use provided F if available
            # Format the response data
            results = []
            for reading in readings:
                results.append({ir_deg,
                    'timestamp': reading.time.isoformat(),direction_cardinal': reading.wind_direction_cardinal,
                    'model': reading.model,  'speed': {
                    'sensor_id': reading.sensor_id,
                    'location': reading.location,  # Include source location': reading.wind_avg_mph,
                    'temperature': {m_s,
                        'celsius': reading.temperature_C,
                        'fahrenheit': reading.temperature_F or reading.calculated_temperature_F  # Use provided F if available
                    },
                    'humidity': reading.humidity,xed the quote mismatch here - was 'rain": {'
                    'wind': {
                        'direction_degrees': reading.wind_dir_deg,
                        'direction_cardinal': reading.wind_direction_cardinal,
                        'speed': {nstallation or last reset"
                            'avg_m_s': reading.wind_avg_m_s,,
                            'avg_mph': reading.wind_avg_mph,  "recent": {
                            'max_m_s': reading.wind_max_m_s,evious_reading_inches": reading.rainfall_since_previous,
                            'max_mph': reading.wind_max_mphinches": reading.get_rainfall_since(hours=1),
                        }ding.get_rainfall_since(hours=24),
                    },          "description": "Rainfall measured over recent time periods"
                    'rain': {  # Fixed the quote mismatch here - was 'rain": {'            }
                        "counter": {
                            "total_mm": reading.rain_mm,reading.uv,
                            "total_inches": reading.rain_inches,.uvi,
                            "description": "Cumulative rainfall counter since station installation or last reset"ux
                        },
                        "recent": {
                            "since_previous_reading_inches": reading.rainfall_since_previous,
                            "last_hour_inches": reading.get_rainfall_since(hours=1),
                            "last_24h_inches": reading.get_rainfall_since(hours=24),
                            "description": "Rainfall measured over recent time periods"
                        }ime_info = {
                    },        'start_time': start_time.isoformat(),
                    'uv': reading.uv,nd_time.isoformat(),
                    'uvi': reading.uvi,': duration.total_seconds(),
                    'light_lux': reading.light_lux: duration.total_seconds() / 60,
                })uration.total_seconds() / 3600
            
            # Include time interval information
            time_info = {}eturn JsonResponse({
            if len(readings) >= 2:s', 
                duration = end_time - start_time),
                time_info = {: time_info,
                    'start_time': start_time.isoformat(),
                    'end_time': end_time.isoformat(),
                    'duration_seconds': duration.total_seconds(),
                    'duration_minutes': duration.total_seconds() / 60,    return JsonResponse({
                    'duration_hours': duration.total_seconds() / 3600'success',
                }
                            'message': 'No readings found',

















        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)    except Exception as e:                    })                'readings': []                'message': 'No readings found',                'count': 0,                'status': 'success',            return JsonResponse({        else:            })                'readings': results                'time_info': time_info,                'count': len(results),                'status': 'success',             return JsonResponse({                'readings': []
            })
        
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
