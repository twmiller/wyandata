import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.db import close_old_connections
from .models import OutdoorWeatherReading, IndoorSensor

class WeatherDataConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for real-time weather data updates"""

    async def connect(self):
        """Connect to the weather data group"""
        # Join the weather data group
        await self.channel_layer.group_add(
            "weather_data",
            self.channel_name
        )
        await self.accept()
        
        # Send the latest data to the newly connected client
        latest_data = await self.get_latest_data()
        if latest_data:
            await self.send(text_data=json.dumps(latest_data))

    async def disconnect(self, close_code):
        """Disconnect from the weather data group"""
        await self.channel_layer.group_discard(
            "weather_data",
            self.channel_name
        )
        # Close any open database connections
        await database_sync_to_async(close_old_connections)()

    @database_sync_to_async
    def get_latest_data(self):
        """Get the latest weather data from the database"""
        try:
            # Close any old connections before making new queries
            close_old_connections()
            
            # Get the latest outdoor reading
            outdoor_reading = OutdoorWeatherReading.objects.order_by('-time').first()
            
            # Get the latest indoor reading
            indoor_reading = IndoorSensor.objects.order_by('-time').first()
            
            if not outdoor_reading:
                return None
                
            # Format the data for WebSocket
            data = {
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
                        "total_mm": outdoor_reading.rain_mm,
                        "total_inches": outdoor_reading.rain_inches,
                        "since_previous_inches": outdoor_reading.rainfall_since_previous
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
            
            # Add indoor data if available
            if indoor_reading:
                data['indoor'] = {
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
                
                # Add pressure data if available
                if hasattr(indoor_reading, 'pressure_hPa') and indoor_reading.pressure_hPa is not None:
                    data['indoor']['pressure'] = {
                        'hPa': indoor_reading.pressure_hPa,
                        'inHg': indoor_reading.pressure_inHg
                    }
            
            # Get all secondary indoor sensors (non-main indoor sensor)
            ambient_sensors = []
            
            # Get all recent indoor sensors with locations (last reading from each unique sensor/channel combo)
            if indoor_reading:
                main_indoor_key = f"{indoor_reading.sensor_id}_{indoor_reading.channel}"
                
                # Find additional indoor sensors (including WH31B sensors with locations)
                recent_sensors = {}
                for sensor in IndoorSensor.objects.filter(location__isnull=False).order_by('-time'):
                    key = f"{sensor.sensor_id}_{sensor.channel}"
                    if key != main_indoor_key and key not in recent_sensors:
                        recent_sensors[key] = sensor
                
                # Add each ambient sensor to the data
                for sensor in recent_sensors.values():
                    sensor_data = {
                        "model": sensor.model,
                        "sensor_id": sensor.sensor_id,
                        "channel": sensor.channel,
                        "location": sensor.location,
                        "temperature": {
                            "celsius": sensor.temperature_C,
                            "fahrenheit": sensor.temperature_F or sensor.calculated_temperature_F  # Use provided F if available
                        },
                        "humidity": sensor.humidity,
                        "timestamp": sensor.time.isoformat()
                    }
                    ambient_sensors.append(sensor_data)
            
            # Add ambient sensors to the response if available
            if ambient_sensors:
                data['ambient_sensors'] = ambient_sensors
            
            return data
            
        except Exception as e:
            print(f"Error retrieving latest weather data: {e}")
            return None
        finally:
            # Always close connections
            close_old_connections()

    # Method called when receiving a message from the group
    async def weather_update(self, event):
        """Handle updates from weather data group"""
        # Send the update to the WebSocket
        await self.send(text_data=json.dumps(event["data"]))
