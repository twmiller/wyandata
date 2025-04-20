import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from asgiref.sync import async_to_sync
from .models import SolarControllerData

class SolarDataConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for real-time solar data updates"""

    async def connect(self):
        """Connect to the solar data group"""
        # Join the solar data group
        await self.channel_layer.group_add(
            "solar_data",
            self.channel_name
        )
        await self.accept()
        
        # Send the latest data to the newly connected client
        latest_data = await self.get_latest_data()
        if latest_data:
            await self.send(text_data=json.dumps(latest_data))

    async def disconnect(self, close_code):
        """Disconnect from the solar data group"""
        await self.channel_layer.group_discard(
            "solar_data",
            self.channel_name
        )

    @database_sync_to_async
    def get_latest_data(self):
        """Get the latest solar data from the database"""
        try:
            latest = SolarControllerData.objects.first()  # Using the ordering from model Meta
            if not latest:
                return None
                
            # Ensure charging_mode is consistently a string
            charging_mode = latest.charging_mode
            if charging_mode is not None:
                if isinstance(charging_mode, (int, float)):
                    charging_mode = str(charging_mode)
            
            return {
                "timestamp": latest.timestamp.isoformat(),
                "pv_array": {
                    "voltage": latest.pv_array_voltage,
                    "current": latest.pv_array_current,
                    "power": latest.pv_array_power
                },
                "battery": {
                    "voltage": latest.battery_voltage,
                    "charging_current": latest.battery_charging_current,
                    "charging_power": latest.battery_charging_power,
                    "temperature": latest.battery_temp
                },
                "load": {
                    "voltage": latest.load_voltage,
                    "current": latest.load_current,
                    "power": latest.load_power
                },
                "controller": {
                    "temperature": latest.controller_temp,
                    "charging_mode": charging_mode
                }
            }
        except Exception as e:
            print(f"Error retrieving latest solar data: {e}")
            return None

    # Method called when receiving a message from the group
    async def solar_update(self, event):
        """Handle updates from solar data group"""
        # Send the update to the WebSocket
        await self.send(text_data=json.dumps(event["data"]))
