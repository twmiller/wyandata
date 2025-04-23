# system/views.py

from django.http import JsonResponse
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.utils import timezone
from .models import Host, MetricValue, MetricType
from django.conf import settings
import pytz  # Import pytz for timezone handling

@api_view(['GET'])
def get_hosts(request):
    """Return all registered hosts"""
    hosts = Host.objects.all().order_by('hostname')
    hosts_data = []
    
    for host in hosts:
        host_data = {
            'id': str(host.id),
            'hostname': host.hostname,
            'system_type': host.system_type,
            'ip_address': host.ip_address,
            'is_active': host.is_active,
            'last_seen': host.last_seen.isoformat() if host.last_seen else None,
        }
        hosts_data.append(host_data)
    
    return Response(hosts_data)

@api_view(['GET'])
def get_host_metrics(request, host_id):
    """Return the latest metrics for a specific host"""
    try:
        host = Host.objects.get(pk=host_id)
    except Host.DoesNotExist:
        return Response({'error': 'Host not found'}, status=404)
    
    # Find the latest metrics for each metric type
    latest_metrics = {}
    
    # Get all metric values for this host
    metrics = MetricValue.objects.filter(host=host).order_by('-timestamp')
    
    # Group by metric type and get the latest
    for metric in metrics:
        metric_name = metric.metric_type.name
        if metric_name not in latest_metrics:
            # Add the metric if we haven't seen this type yet
            latest_metrics[metric_name] = {
                'value': metric.value,
                'unit': metric.metric_type.unit,
                'timestamp': metric.timestamp.isoformat(),
                'category': metric.metric_type.category,
            }
    
    return Response({
        'host_id': str(host.id),
        'hostname': host.hostname,
        'metrics': latest_metrics
    })

@api_view(['GET'])
def get_host_details(request, host_id):
    """Return detailed information about a specific host"""
    try:
        host = Host.objects.get(pk=host_id)
    except Host.DoesNotExist:
        return Response({'error': 'Host not found'}, status=404)
    
    # Get storage devices for this host
    storage_devices = []
    for device in host.storage_devices.all():
        storage_devices.append({
            'id': str(device.id),
            'name': device.name,
            'device_type': device.device_type,
            'total_bytes': device.total_bytes,
        })
    
    # Get network interfaces for this host
    network_interfaces = []
    for interface in host.network_interfaces.all():
        network_interfaces.append({
            'id': str(interface.id),
            'name': interface.name,
            'mac_address': interface.mac_address,
            'ip_address': interface.ip_address,
            'is_up': interface.is_up,
        })
    
    # Build the detailed response
    host_details = {
        'id': str(host.id),
        'hostname': host.hostname,
        'system_type': host.system_type,
        'ip_address': host.ip_address,
        'cpu_model': host.cpu_model,
        'cpu_cores': host.cpu_cores,
        'ram_total': host.ram_total,
        'gpu_model': host.gpu_model,
        'os_version': host.os_version,
        'is_active': host.is_active,
        'last_seen': host.last_seen.isoformat() if host.last_seen else None,
        'storage_devices': storage_devices,
        'network_interfaces': network_interfaces,
    }
    
    return Response(host_details)

@api_view(['GET'])
def get_host_metrics_history(request, host_id):
    """Return historical metrics for a specific host based on count rather than time"""
    try:
        host = Host.objects.get(pk=host_id)
    except Host.DoesNotExist:
        return Response({'error': 'Host not found'}, status=404)
    
    # Get query parameters - using count instead of hours
    count = min(int(request.GET.get('count', 180)), 1000)  # Default 180 metrics, max 1000
    interval_minutes = max(1, min(int(request.GET.get('interval', 5)), 60))  # Default 5, min 1, max 60
    
    # Get specific metrics if requested
    requested_metrics = request.GET.get('metrics')
    metric_names = requested_metrics.split(',') if requested_metrics else None
    
    # Get total count of metrics for this host for debugging
    total_count = MetricValue.objects.filter(host=host).count()
    
    # Get all available metric types for this host
    metric_types = MetricType.objects.filter(values__host=host).distinct()
    
    if metric_names:
        metric_types = metric_types.filter(name__in=metric_names)
    
    # Get data for each metric type
    metrics_list = []
    
    for metric_type in metric_types:
        # Get latest 'count' metrics for this type
        values = MetricValue.objects.filter(
            host=host, 
            metric_type=metric_type
        ).order_by('-timestamp')[:count]
        
        # Re-sort chronologically for the response
        values = sorted(values, key=lambda x: x.timestamp)
        
        # Format data points
        data_points = [
            {
                'timestamp': value.timestamp.isoformat() if value.timestamp else None,
                'value': float(value.value) if value.value is not None else None
            }
            for value in values
        ]
        
        if data_points:
            metrics_list.append({
                'name': metric_type.name,
                'category': metric_type.category,
                'unit': metric_type.unit,
                'data_points': data_points
            })
    
    # Find time range from the collected data points if any exist
    start_time = None
    end_time = None
    duration_minutes = None
    
    all_timestamps = []
    for metric in metrics_list:
        for point in metric.get('data_points', []):
            if point.get('timestamp'):
                all_timestamps.append(point['timestamp'])
    
    if all_timestamps:
        all_timestamps.sort()
        start_time = all_timestamps[0]
        end_time = all_timestamps[-1]
        
        # Calculate duration
        from datetime import datetime
        start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00') 
                                         if start_time.endswith('Z') else start_time)
        end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00') 
                                       if end_time.endswith('Z') else end_time)
        duration_minutes = (end_dt - start_dt).total_seconds() / 60
    
    return Response({
        'host_id': str(host.id),
        'hostname': host.hostname,
        'count_requested': count,
        'data_count': sum(len(m.get('data_points', [])) for m in metrics_list),
        'time_range': {
            'start': start_time,
            'end': end_time,
            'duration_minutes': duration_minutes
        },
        'interval_minutes': interval_minutes,
        'metrics': metrics_list,
        'total_metrics_in_db': total_count
    })

@api_view(['GET'])
def get_host_available_metrics(request, host_id):
    """Return all available metrics for a specific host"""
    try:
        host = Host.objects.get(pk=host_id)
    except Host.DoesNotExist:
        return Response({'error': 'Host not found'}, status=404)
    
    # Get all metric types for this host
    metric_types = MetricType.objects.filter(
        values__host=host
    ).distinct().order_by('category', 'name')
    
    # Group metrics by category
    metrics_by_category = {}
    for metric_type in metric_types:
        category = metric_type.category
        if category not in metrics_by_category:
            metrics_by_category[category] = []
        
        metrics_by_category[category].append({
            'name': metric_type.name,
            'description': metric_type.description,
            'unit': metric_type.unit,
            'data_type': metric_type.data_type,
        })
    
    # Get latest reading time
    latest_reading = MetricValue.objects.filter(
        host=host
    ).order_by('-timestamp').first()
    
    latest_timestamp = latest_reading.timestamp if latest_reading else None
    
    return Response({
        'host_id': str(host.id),
        'hostname': host.hostname,
        'latest_data_timestamp': latest_timestamp.isoformat() if latest_timestamp else None,
        'metrics': metrics_by_category
    })