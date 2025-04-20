from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.utils import timezone
from datetime import timedelta
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import json

from .models import SolarControllerData
from .utils import get_solar_data

# REST API ViewSet for retrieving solar data
class SolarDataViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for retrieving solar controller data
    """
    queryset = SolarControllerData.objects.all().order_by('-timestamp')
    permission_classes = [AllowAny]  # Adjust permissions as needed
    
    def list(self, request):
        """Get the latest solar data"""
        try:
            latest_data = self.queryset.first()
            if not latest_data:
                return Response(
                    {"error": "No solar data available"}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            data = self.format_solar_data(latest_data)
            return Response(data)
        except Exception as e:
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def history(self, request):
        """Get historical solar data"""
        hours = int(request.query_params.get('hours', 24))
        interval = request.query_params.get('interval', 'raw')
        
        since = timezone.now() - timedelta(hours=hours)
        data_points = self.queryset.filter(timestamp__gte=since)
        
        if interval == 'hourly' and hours > 24:
            # Group by hour for longer periods
            # This would require a more complex query with aggregation
            # For simplicity, just sample one reading per hour
            pass
        
        result = {
            "timestamps": [],
            "pv_power": [],
            "battery_voltage": [],
            "battery_power": [],
            "load_power": []
        }
        
        for entry in data_points:
            result["timestamps"].append(entry.timestamp.isoformat())
            result["pv_power"].append(entry.pv_array_power)
            result["battery_voltage"].append(entry.battery_voltage)
            result["battery_power"].append(entry.battery_charging_power)
            result["load_power"].append(entry.load_power)
        
        return Response(result)
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get statistics for solar data"""
        hours = int(request.query_params.get('hours', 24))
        since = timezone.now() - timedelta(hours=hours)
        
        data_points = self.queryset.filter(timestamp__gte=since)
        
        if not data_points:
            return Response(
                {"error": "No data available for the specified period"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Calculate some basic statistics
        pv_power_values = [dp.pv_array_power for dp in data_points if dp.pv_array_power is not None]
        battery_voltage_values = [dp.battery_voltage for dp in data_points if dp.battery_voltage is not None]
        load_power_values = [dp.load_power for dp in data_points if dp.load_power is not None]
        
        stats = {
            "period_hours": hours,
            "data_point_count": data_points.count(),
            "pv_power": {
                "max": max(pv_power_values) if pv_power_values else None,
                "min": min(pv_power_values) if pv_power_values else None,
                "avg": sum(pv_power_values) / len(pv_power_values) if pv_power_values else None
            },
            "battery_voltage": {
                "max": max(battery_voltage_values) if battery_voltage_values else None,
                "min": min(battery_voltage_values) if battery_voltage_values else None,
                "avg": sum(battery_voltage_values) / len(battery_voltage_values) if battery_voltage_values else None
            },
            "load_power": {
                "max": max(load_power_values) if load_power_values else None,
                "min": min(load_power_values) if load_power_values else None,
                "avg": sum(load_power_values) / len(load_power_values) if load_power_values else None
            }
        }
        
        return Response(stats)
    
    def format_solar_data(self, data_point):
        """Format a solar data point for API response"""
        return {
            "timestamp": data_point.timestamp.isoformat(),
            "pv_array": {
                "voltage": data_point.pv_array_voltage,
                "current": data_point.pv_array_current,
                "power": data_point.pv_array_power
            },
            "battery": {
                "voltage": data_point.battery_voltage,
                "charging_current": data_point.battery_charging_current,
                "charging_power": data_point.battery_charging_power,
                "temperature": data_point.battery_temp,
                "type": data_point.battery_type,
                "capacity": data_point.battery_capacity
            },
            "load": {
                "voltage": data_point.load_voltage,
                "current": data_point.load_current,
                "power": data_point.load_power
            },
            "controller": {
                "temperature": data_point.controller_temp,
                "heat_sink_temperature": data_point.heat_sink_temp,
                "charging_mode": data_point.charging_mode
            },
            "settings": {
                "high_voltage_disconnect": data_point.high_voltage_disconnect,
                "charging_limit_voltage": data_point.charging_limit_voltage,
                "equalization_voltage": data_point.equalization_voltage,
                "boost_voltage": data_point.boost_voltage,
                "float_voltage": data_point.float_voltage,
                "low_voltage_reconnect": data_point.low_voltage_reconnect,
                "low_voltage_disconnect": data_point.low_voltage_disconnect
            }
        }

# Data upload endpoint (already implemented in your version)
@api_view(['POST'])
@permission_classes([AllowAny])  # For internal network use only
def solar_data_upload(request):
    """
    Endpoint to receive solar controller data from external scripts
    """
    try:
        data = request.data
        
        # Extract the data we need for our model
        controller_data = {}
        
        # Process controller info
        if 'controller_info' in data:
            for key, info in data['controller_info'].items():
                controller_data[key] = info['value']
        
        # Process real-time data
        if 'real_time_data' in data:
            for key, info in data['real_time_data'].items():
                controller_data[key] = info['value']
        
        # Process settings
        if 'settings' in data:
            for key, info in data['settings'].items():
                controller_data[key] = info['value']
        
        # Extract individual fields if data is flat
        if not controller_data:
            controller_data = data
        
        # Create and save the model
        solar_data = SolarControllerData(**controller_data)
        solar_data.save()
        
        # Format data for WebSocket
        ws_data = {
            "timestamp": solar_data.timestamp.isoformat(),
            "pv_array": {
                "voltage": solar_data.pv_array_voltage,
                "current": solar_data.pv_array_current,
                "power": solar_data.pv_array_power
            },
            "battery": {
                "voltage": solar_data.battery_voltage,
                "charging_current": solar_data.battery_charging_current,
                "charging_power": solar_data.battery_charging_power,
                "temperature": solar_data.battery_temp
            },
            "load": {
                "voltage": solar_data.load_voltage,
                "current": solar_data.load_current,
                "power": solar_data.load_power
            },
            "controller": {
                "temperature": solar_data.controller_temp,
                "charging_mode": solar_data.charging_mode
            }
        }
        
        # Send update to all WebSocket clients
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            "solar_data",
            {
                "type": "solar_update",
                "data": ws_data
            }
        )
        
        return Response({
            "status": "success", 
            "message": "Solar data saved",
            "timestamp": solar_data.timestamp
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        return Response({
            "status": "error", 
            "message": str(e)
        }, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([AllowAny])  # For internal network use only
def cleanup_solar_data(request):
    """
    Endpoint to clean up old solar controller data
    """
    try:
        # Default to 7 days if not specified
        days = int(request.data.get('days', 7))
        
        # Calculate the cutoff date
        cutoff_date = timezone.now() - timedelta(days=days)
        
        # Delete old records
        old_records = SolarControllerData.objects.filter(timestamp__lt=cutoff_date)
        count = old_records.count()
        old_records.delete()
        
        return Response({
            "status": "success", 
            "message": f"Deleted {count} records older than {cutoff_date.strftime('%Y-%m-%d')}",
            "deleted_count": count,
            "cutoff_date": cutoff_date
        })
        
    except Exception as e:
        return Response({
            "status": "error", 
            "message": str(e)
        }, status=status.HTTP_400_BAD_REQUEST)
