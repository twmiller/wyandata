from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
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
