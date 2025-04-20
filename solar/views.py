from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny
from django.utils import timezone
from datetime import timedelta

from .models import SolarControllerData
from .utils import get_solar_data

class SolarDataViewSet(viewsets.ViewSet):
    """
    API endpoint to get solar controller data
    """
    
    def list(self, request):
        """Get the most recent solar data entry"""
        try:
            latest_data = SolarControllerData.objects.first()  # Model is ordered by -timestamp
            if not latest_data:
                return Response({"error": "No solar data available"}, status=status.HTTP_404_NOT_FOUND)
            
            data = {
                "timestamp": latest_data.timestamp,
                "pv_array": {
                    "voltage": latest_data.pv_array_voltage,
                    "current": latest_data.pv_array_current,
                    "power": latest_data.pv_array_power
                },
                "battery": {
                    "voltage": latest_data.battery_voltage,
                    "charging_current": latest_data.battery_charging_current,
                    "charging_power": latest_data.battery_charging_power,
                    "temperature": latest_data.battery_temp
                },
                "load": {
                    "voltage": latest_data.load_voltage,
                    "current": latest_data.load_current,
                    "power": latest_data.load_power
                },
                "controller": {
                    "temperature": latest_data.controller_temp,
                    "heat_sink_temperature": latest_data.heat_sink_temp,
                    "charging_mode": latest_data.charging_mode
                }
            }
            
            return Response(data)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def history(self, request):
        """Get historical solar data for specified period"""
        days = int(request.query_params.get('days', 1))
        since = timezone.now() - timedelta(days=days)
        
        data_points = SolarControllerData.objects.filter(timestamp__gte=since)
        
        # Create time series data for charts
        timestamps = [entry.timestamp for entry in data_points]
        pv_power = [entry.pv_array_power for entry in data_points]
        battery_voltage = [entry.battery_voltage for entry in data_points]
        
        return Response({
            "timestamps": timestamps,
            "pv_power": pv_power,
            "battery_voltage": battery_voltage
        })
    
    @action(detail=False, methods=['get'])
    def live(self, request):
        """Get live data directly from the controller"""
        data = get_solar_data()
        if not data:
            return Response({"error": "Could not connect to controller"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        
        return Response(data)

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
        
        # Create and save the model
        solar_data = SolarControllerData(**controller_data)
        solar_data.save()
        
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
