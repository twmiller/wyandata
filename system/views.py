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
    """Return historical metrics for a specific host"""
    try:
        host = Host.objects.get(pk=host_id)
    except Host.DoesNotExist:
        return Response({'error': 'Host not found'}, status=404)
    
    # Get query parameters
    hours = min(int(request.GET.get('hours', 3)), 48)  # Default 3, max 48 hours
    interval_minutes = max(1, min(int(request.GET.get('interval', 5)), 60))  # Default 5, min 1, max 60
    
    # Get specific metrics if provided
    requested_metrics = request.GET.get('metrics')
    metric_names = requested_metrics.split(',') if requested_metrics else None
    
    # For large datasets, use direct SQL with time-based partitioning
    from django.db import connection
    
    # Calculate time range with explicit UTC handling
    end_time = timezone.now()
    start_time = end_time - timezone.timedelta(hours=hours)
    
    # Print out full debug data
    print(f"Current time (server): {timezone.now()}")
    print(f"Query time range: {start_time} to {end_time}")
    print(f"Host ID: {host_id}")
    
    # For safety, force times to be timezone-aware 
    # Use pytz.UTC instead of timezone.utc
    if timezone.is_naive(start_time):
        start_time = timezone.make_aware(start_time, pytz.UTC)
    if timezone.is_naive(end_time):
        end_time = timezone.make_aware(end_time, pytz.UTC)
    
    # For cleaner SQL, format timestamps as strings
    start_time_str = start_time.strftime('%Y-%m-%d %H:%M:%S%z')
    end_time_str = end_time.strftime('%Y-%m-%d %H:%M:%S%z')
    
    # Run direct SQL query
    with connection.cursor() as cursor:
        # First get all available metric types
        cursor.execute("""
            SELECT DISTINCT mt.id, mt.name, mt.unit, mt.category
            FROM system_metrictype mt
            JOIN system_metricvalue mv ON mv.metric_type_id = mt.id
            WHERE mv.host_id = %s
        """, [host_id])
        
        available_metrics = [
            {'id': row[0], 'name': row[1], 'unit': row[2], 'category': row[3]}
            for row in cursor.fetchall()
        ]
        
        # Filter metric types if requested
        if metric_names:
            available_metrics = [m for m in available_metrics if m['name'] in metric_names]
    
    print(f"Available metrics: {[m['name'] for m in available_metrics]}")
    
    # Get data for each metric type
    metrics_list = []
    
    for metric in available_metrics:
        # Use raw SQL query with proper timestamp comparison and efficient bucketing
        query = """
            WITH raw_data AS (
                SELECT 
                    mv.timestamp, 
                    CASE 
                        WHEN mt.data_type = 'FLOAT' THEN mv.float_value
                        WHEN mt.data_type = 'INT' THEN mv.int_value::text::float
                        WHEN mt.data_type = 'BOOL' THEN mv.bool_value::text::float
                        ELSE NULL
                    END AS value
                FROM system_metricvalue mv
                JOIN system_metrictype mt ON mv.metric_type_id = mt.id
                WHERE 
                    mv.host_id = %s 
                    AND mt.id = %s
                    AND mv.timestamp >= %s
                    AND mv.timestamp <= %s
                ORDER BY mv.timestamp
            ),
            -- Create buckets by extracting epoch and dividing by interval in seconds
            bucketed AS (
                SELECT 
                    timestamp, 
                    value,
                    FLOOR(EXTRACT(EPOCH FROM timestamp) / (%s * 60)) AS bucket
                FROM raw_data
            )
            -- Get one sample per bucket (first in each group)
            SELECT timestamp, value
            FROM (
                SELECT 
                    timestamp,
                    value,
                    ROW_NUMBER() OVER (PARTITION BY bucket ORDER BY timestamp) AS rn
                FROM bucketed
            ) ranked
            WHERE rn = 1
            ORDER BY timestamp
        """
        
        with connection.cursor() as cursor:
            cursor.execute(query, [
                host_id,
                metric['id'],
                start_time,
                end_time,
                interval_minutes
            ])
            
            # Add timezone info to the timestamps when converting back to Python
            data_points = [
                {
                    'timestamp': row[0].isoformat(),
                    'value': float(row[1]) if row[1] is not None else None
                }
                for row in cursor.fetchall()
            ]
        
        # Only include metrics that have data points
        if data_points:
            metrics_list.append({
                'name': metric['name'],
                'category': metric['category'],
                'unit': metric['unit'],
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
        'metrics': metrics_list,
        'debug_info': {
            'server_time': timezone.now().isoformat(),
            'timezone_name': timezone.get_current_timezone_name(),
            'use_tz': getattr(settings, 'USE_TZ', False),
            # Update this line to avoid using timezone.utc
            'database_time': timezone.now().astimezone(pytz.UTC).isoformat()
        }
    })