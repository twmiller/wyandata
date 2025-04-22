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
    
    # Important: Your debug info shows that server time is different from database time
    # The server time is naive in America/Denver timezone: 2025-04-22T16:00:10.959957
    # The database time is aware in UTC: 2025-04-22T22:00:10.959989+00:00
    
    # Calculate time range based on naive current time
    end_time_naive = timezone.now()
    start_time_naive = end_time_naive - timezone.timedelta(hours=hours)
    
    print(f"Using naive time range: {start_time_naive} to {end_time_naive}")
    
    # No timezone conversion needed since USE_TZ is False in settings
    # and we're querying directly from the database
    
    # Use raw SQL query - first, find any metrics in the last 24 hours to verify timing
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT 
                MIN(mv.timestamp) as earliest,
                MAX(mv.timestamp) as latest,
                COUNT(*) as count
            FROM system_metricvalue mv
            WHERE mv.host_id = %s 
            AND mv.timestamp > NOW() - INTERVAL '24 hours'
        """, [host_id])
        
        row = cursor.fetchone()
        earliest = row[0]
        latest = row[1]
        count = row[2]
        
        print(f"Debug: Found {count} metrics in last 24 hours.")
        print(f"Debug: Earliest is {earliest}, Latest is {latest}")
        
    # Get distinct metric types
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT DISTINCT mt.id, mt.name, mt.unit, mt.category
            FROM system_metrictype mt
            JOIN system_metricvalue mv ON mv.metric_type_id = mt.id
            WHERE mv.host_id = %s
            AND mv.timestamp > NOW() - INTERVAL %s
        """, [host_id, f"{hours*2} hours"])  # Double hours as a safety margin
        
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
                    -- Use NOW() and a direct hour computation for more reliable time comparison
                    AND mv.timestamp > NOW() - INTERVAL %s
                    AND mv.timestamp <= NOW()
                ORDER BY mv.timestamp
            ),
            bucketed AS (
                SELECT 
                    timestamp, 
                    value,
                    FLOOR(EXTRACT(EPOCH FROM timestamp) / (%s * 60)) AS bucket
                FROM raw_data
            )
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
                f"{hours} hours",  # Use SQL interval notation
                interval_minutes
            ])
            
            # Process the results
            data_points = [
                {
                    'timestamp': row[0].isoformat() if row[0] else None,
                    'value': float(row[1]) if row[1] is not None else None
                }
                for row in cursor.fetchall()
            ]
            
            print(f"Metric {metric['name']}: found {len(data_points)} data points")
        
        # Only include metrics that have data points
        if data_points:
            metrics_list.append({
                'name': metric['name'],
                'category': metric['category'],
                'unit': metric['unit'],
                'data_points': data_points
            })
    
    # Set response times using the same method as the database query
    actual_end_time = timezone.now()
    actual_start_time = actual_end_time - timezone.timedelta(hours=hours)
    
    return Response({
        'host_id': str(host.id),
        'hostname': host.hostname,
        'time_range': {
            'start': actual_start_time.isoformat(),
            'end': actual_end_time.isoformat(),
            'duration_hours': hours
        },
        'interval_minutes': interval_minutes,
        'metrics': metrics_list,
        'debug_info': {
            'server_time': str(timezone.now()),
            'timezone_name': timezone.get_current_timezone_name(),
            'use_tz': getattr(settings, 'USE_TZ', False),
            'database_time_offset': (timezone.now().astimezone(pytz.UTC) - timezone.now()).total_seconds() / 3600,
            'query_timestamp_start': str(earliest) if 'earliest' in locals() and earliest else None,
            'query_timestamp_end': str(latest) if 'latest' in locals() and latest else None,
            'query_count_24h': count if 'count' in locals() else None
        }
    })