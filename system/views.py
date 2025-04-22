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
    
    # Directly use SQL query without timezone issues
    from django.db import connection
    
    # Skip all timezone handling and use direct database queries
    with connection.cursor() as cursor:
        # Use direct SQL to get metrics from database using NOW() function
        cursor.execute("""
            SELECT 
                MIN(timestamp) as earliest_time,
                MAX(timestamp) as latest_time,
                COUNT(*) as count  
            FROM system_metricvalue 
            WHERE host_id = %s
            AND timestamp > NOW() - INTERVAL %s
        """, [host_id, f"{hours} hours"])
        
        time_data = cursor.fetchone()
        earliest_time = time_data[0]
        latest_time = time_data[1]
        total_count = time_data[2]
        
        # Get all available metrics
        cursor.execute("""
            SELECT DISTINCT mt.id, mt.name, mt.unit, mt.category
            FROM system_metricvalue mv
            JOIN system_metrictype mt ON mv.metric_type_id = mt.id
            WHERE mv.host_id = %s
            AND mv.timestamp > NOW() - INTERVAL %s
        """, [host_id, f"{hours} hours"])
        
        metric_types = [
            {'id': row[0], 'name': row[1], 'unit': row[2], 'category': row[3]}
            for row in cursor.fetchall()
        ]
    
    # Filter metric types if requested
    if metric_names:
        metric_types = [m for m in metric_types if m['name'] in metric_names]
    
    # Get data for each metric type
    metrics_list = []
    
    for metric in metric_types:
        with connection.cursor() as cursor:
            cursor.execute("""
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
                        AND mv.timestamp > NOW() - INTERVAL %s
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
            """, [
                host_id,
                metric['id'],
                f"{hours} hours", 
                interval_minutes
            ])
            
            data_points = [
                {
                    'timestamp': row[0].isoformat() if row[0] else None,
                    'value': float(row[1]) if row[1] is not None else None
                }
                for row in cursor.fetchall()
            ]
        
        if data_points:
            metrics_list.append({
                'name': metric['name'],
                'category': metric['category'],
                'unit': metric['unit'],
                'data_points': data_points
            })
    
    # Get safe start and end times from the database
    start_time = earliest_time if earliest_time else None
    end_time = latest_time if latest_time else None
    
    return Response({
        'host_id': str(host.id),
        'hostname': host.hostname,
        'time_range': {
            'start': start_time.isoformat() if start_time else None,
            'end': end_time.isoformat() if end_time else None,
            'duration_hours': hours
        },
        'interval_minutes': interval_minutes,
        'metrics': metrics_list,
        'records_found': total_count
    })