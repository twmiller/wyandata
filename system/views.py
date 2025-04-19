# system/views.py

from django.http import JsonResponse
from rest_framework.decorators import api_view
from rest_framework.response import Response
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

# system/views.py - add this function

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