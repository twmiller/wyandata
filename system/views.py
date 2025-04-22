# system/views.py

from django.http import JsonResponse
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.utils import timezone
from .models import Host, MetricValue, MetricType

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
    """Return historical metrics for a specific host"""
    try:
        host = Host.objects.get(pk=host_id)
    except Host.DoesNotExist:
        return Response({'error': 'Host not found'}, status=404)
    
    # Get query parameters
    hours = min(int(request.GET.get('hours', 3)), 12)  # Default 3, max 12 hours
    interval_minutes = max(1, min(int(request.GET.get('interval', 5)), 60))  # Default 5, min 1, max 60
    
    # Get specific metrics if provided
    requested_metrics = request.GET.get('metrics')
    metric_names = requested_metrics.split(',') if requested_metrics else None
    
    # Calculate time range
    end_time = timezone.now()
    start_time = end_time - timezone.timedelta(hours=hours)
    
    # Debug output
    print(f"Querying metrics for host {host.hostname} from {start_time} to {end_time}")
    
    # Direct debugging check for metrics in this time range
    metric_count = MetricValue.objects.filter(
        host=host, 
        timestamp__gte=start_time
    ).count()
    print(f"Total metrics found: {metric_count}")
    
    # Get all metric values within the time range, grouped by type
    metrics_list = []
    
    # First get all distinct metric types for this host
    metric_types = MetricType.objects.filter(
        values__host=host,
        values__timestamp__gte=start_time,
        values__timestamp__lte=end_time
    ).distinct()
    
    print(f"Found {metric_types.count()} distinct metric types")
    
    # Process each metric type
    for metric_type in metric_types:
        # Skip if we're filtering and this type isn't requested
        if metric_names and metric_type.name not in metric_names:
            continue
            
        # Get values for this metric type
        values = MetricValue.objects.filter(
            host=host,
            metric_type=metric_type,
            timestamp__gte=start_time,
            timestamp__lte=end_time
        ).order_by('timestamp')
        
        print(f"Metric type {metric_type.name}: found {values.count()} values")
        
        if not values.exists():
            continue
            
        # Apply downsampling if needed
        data_points = []
        last_timestamp = None
        interval_delta = timezone.timedelta(minutes=interval_minutes)
        
        for value in values:
            # Include this point if it's our first point or if enough time has passed
            if last_timestamp is None or (value.timestamp - last_timestamp) >= interval_delta:
                data_points.append({
                    'timestamp': value.timestamp.isoformat(),
                    'value': value.value
                })
                last_timestamp = value.timestamp
        
        # Add this metric type to our results if we have data points
        if data_points:
            metrics_list.append({
                'name': metric_type.name,
                'category': metric_type.category,
                'unit': metric_type.unit,
                'data_points': data_points
            })
    
    print(f"Returning {len(metrics_list)} metrics with data")
    
    return Response({
        'host_id': str(host.id),
        'hostname': host.hostname,
        'time_range': {
            'start': start_time.isoformat(),
            'end': end_time.isoformat(),
            'duration_hours': (end_time - start_time).total_seconds() / 3600.0
        },
        'interval_minutes': interval_minutes,
        'metrics': metrics_list
    })