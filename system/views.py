# system/views.py

from django.http import JsonResponse
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.utils import timezone
from .models import Host, MetricValue, MetricType
from django.conf import settings
import pytz  # Import pytz for timezone handling
import logging
import sys

# Set up a logger that will definitely output to the console
logger = logging.getLogger('system.views')
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.INFO)
formatter = logging.Formatter('API: %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)
logger.propagate = False  # Prevent duplicate logs

@api_view(['GET'])
def get_hosts(request):
    """Return all registered hosts"""
    hosts = Host.objects.all().order_by('hostname')
    hosts_data = []
    
    for host in hosts:
        # Use the current_status property instead of the is_active field
        host_data = {
            'id': str(host.id),
            'hostname': host.hostname,
            'system_type': host.system_type,
            'ip_address': host.ip_address,
            'is_active': host.current_status,  # Use the property instead of the field
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
        'is_active': host.current_status,  # Use the property instead of the field
        'last_seen': host.last_seen.isoformat() if host.last_seen else None,
        'storage_devices': storage_devices,
        'network_interfaces': network_interfaces,
    }
    
    return Response(host_details)

@api_view(['GET'])
def get_host_metrics_history(request, host_id):
    """Return the absolute freshest metrics for a specific host using the Django ORM"""
    print(f"SYSTEM API: Metrics history request for host {host_id}")
    
    try:
        host = Host.objects.get(pk=host_id)
    except Host.DoesNotExist:
        print(f"SYSTEM API: Host not found: {host_id}")
        logger.warning(f"History request for unknown host: {host_id}")
        return Response({'error': 'Host not found'}, status=404)
    
    # Get query parameters
    count = min(int(request.GET.get('count', 60)), 1000)  # Default 60 metrics, max 1000
    
    # Get specific metrics if requested
    requested_metrics = request.GET.get('metrics')
    metric_names = requested_metrics.split(',') if requested_metrics else None
    
    # Log the request with print to guarantee we see it
    print(f"SYSTEM API: History for {host.hostname} | count={count} | metrics={requested_metrics or 'all'}")
    
    # Use Django's ORM to get metric types - filter by name if specified
    metric_types_query = MetricType.objects.filter(
        values__host=host
    ).distinct()
    
    if metric_names:
        metric_types_query = metric_types_query.filter(name__in=metric_names)
    
    # Get the metric types
    metric_types = metric_types_query.order_by('category', 'name')
    
    # Get fresh data for each metric type
    metrics_list = []
    query_start_time = timezone.now()
    
    for metric_type in metric_types:
        # Get the latest values by primary key
        values = MetricValue.objects.filter(
            host=host,
            metric_type=metric_type
        ).order_by('-id')[:count]
        
        # Format data points - KEEP THE ORIGINAL ORDER
        data_points = []
        for value in values:
            data_points.append({
                'timestamp': value.timestamp.isoformat() if value.timestamp else None,
                'value': float(value.value) if value.value is not None else None
            })
        
        if data_points:
            metrics_list.append({
                'name': metric_type.name,
                'category': metric_type.category,
                'unit': metric_type.unit,
                'data_points': data_points
            })
    
    # Calculate metrics
    data_points_count = sum(len(m.get('data_points', [])) for m in metrics_list)
    query_duration_ms = (timezone.now() - query_start_time).total_seconds() * 1000
    
    # Return with debugging info
    return Response({
        'host_id': str(host.id),
        'hostname': host.hostname,
        'count_requested': count,
        'metrics': metrics_list,
        'metrics_count': data_points_count,
        'query_duration_ms': round(query_duration_ms, 2)
    }, headers={
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        'Pragma': 'no-cache',
        'Expires': '0'
    })

@api_view(['GET'])
def get_host_available_metrics(request, host_id):
    """Return all available metrics for a specific host"""
    try:
        host = Host.objects.get(pk=host_id)
    except Host.DoesNotExist:
        logger.warning(f"Available metrics request for unknown host: {host_id}")
        return Response({'error': 'Host not found'}, status=404)
    
    # Log the request
    logger.info(f"Available metrics request for {host.hostname} ({host_id})")
    
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