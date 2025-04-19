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

    @api_view(['GET'])
    def get_host_details(request, host_id):
        """Return detailed information about a specific host"""
        try:
            host = Host.objects.get(pk=host_id)
        except Host.DoesNotExist:
            return Response({'error': 'Host not found'}, status=404)
        
        # Get storage devices
        storage_devices = []
        for device in host.storage_devices.all():
            storage_devices.append({
                'id': str(device.id),
                'name': device.name,
                'device_type': device.device_type,
                'total_bytes': device.total_bytes,
            })
        
        # Get network interfaces
        network_interfaces = []
        for interface in host.network_interfaces.all():
            network_interfaces.append({
                'id': str(interface.id),
                'name': interface.name,
                'mac_address': interface.mac_address,
                'ip_address': interface.ip_address,
                'is_up': interface.is_up,
            })
        
        # Build response
        host_data = {
            'id': str(host.id),
            'hostname': host.hostname,
            'system_type': host.system_type,
            'ip_address': host.ip_address,
            'cpu_model': host.cpu_model,
            'cpu_cores': host.cpu_cores,
            'ram_total': host.ram_total,
            'gpu_model': host.