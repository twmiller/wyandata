import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
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

    @database_sync_to_async
    def get_latest_data(self):
        """Get the latest weather data from the database"""
        try:
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
                    "temperature": {
                        "celsius": outdoor_reading.temperature_C,
                        "fahrenheit": outdoor_reading.temperature_F
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
                    "temperature": {
                        "celsius": indoor_reading.temperature_C,
                        "fahrenheit": indoor_reading.temperature_F
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
            
            return data
            
        except Exception as e:
            print(f"Error retrieving latest weather data: {e}")
            return None

    # Method called when receiving a message from the group
    async def weather_update(self, event):
        """Handle updates from weather data group"""
        # Send the update to the WebSocket
        await self.send(text_data=json.dumps(event["data"]))
