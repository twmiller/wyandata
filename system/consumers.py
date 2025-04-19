# system/consumers.py

import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from .models import Host, MetricType, MetricValue, StorageDevice, NetworkInterface
from .db_utils import with_retry

class SystemMetricsConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        """Handle WebSocket connection"""
        # Join a group for all system metrics
        self.room_group_name = 'all_systems'
        
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        # Leave the group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        """Handle incoming messages from clients"""
        data = json.loads(text_data)
        message_type = data.get('type')
        
        if message_type == 'register_host':
            await self.handle_host_registration(data)
        elif message_type == 'metrics_update':
            await self.handle_metrics_update(data)
        elif message_type == 'subscribe_host':
            await self.handle_host_subscription(data)
    
    async def handle_host_registration(self, data):
        """Register or update a host in the system"""
        hostname = data.get('hostname')
        system_info = data.get('system_info', {})
        
        # Create or update host record
        host = await self.update_host_record(hostname, system_info)
        
        # Update storage devices
        if 'storage_devices' in data:
            await self.update_storage_devices(host, data['storage_devices'])
        
        # Update network interfaces
        if 'network_interfaces' in data:
            await self.update_network_interfaces(host, data['network_interfaces'])
        
        # Confirm registration
        await self.send(text_data=json.dumps({
            'type': 'registration_confirmed',
            'host_id': str(host.id),
            'timestamp': timezone.now().isoformat()
        }))
    
    async def handle_metrics_update(self, data):
        """Process incoming metrics from client agents"""
        hostname = data.get('hostname')
        metrics = data.get('metrics', {})
        timestamp = timezone.now()
        
        # Ensure host exists
        host = await self.get_host_by_hostname(hostname)
        if not host:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': f'Host {hostname} not registered'
            }))
            return
        
        # Update host's last seen timestamp
        await self.update_host_last_seen(host)
        
        # Store metrics
        for metric_name, value_data in metrics.items():
            await self.store_metric(host, metric_name, value_data, timestamp)
        
        # Broadcast to all connected clients
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'metrics_message',
                'hostname': hostname,
                'host_id': str(host.id),
                'metrics': metrics,
                'timestamp': timestamp.isoformat()
            }
        )
        
        # Also send to the specific host group
        await self.channel_layer.group_send(
            f'host_{host.id}',
            {
                'type': 'metrics_message',
                'hostname': hostname,
                'host_id': str(host.id),
                'metrics': metrics,
                'timestamp': timestamp.isoformat()
            }
        )
    
    async def handle_host_subscription(self, data):
        """Subscribe client to updates for a specific host"""
        host_id = data.get('host_id')
        
        # Add the client to the host-specific group
        if host_id:
            await self.channel_layer.group_add(
                f'host_{host_id}',
                self.channel_name
            )
            
            await self.send(text_data=json.dumps({
                'type': 'subscription_confirmed',
                'host_id': host_id
            }))
    
    async def metrics_message(self, event):
        """Send metrics update to WebSocket clients"""
        # Forward the message to the WebSocket
        await self.send(text_data=json.dumps(event))
    
    # Database helper methods
    @database_sync_to_async
    @with_retry(max_retries=5, retry_delay=0.2)
    def update_host_record(self, hostname, system_info):
        """Create or update a host record"""
        host, created = Host.objects.update_or_create(
            hostname=hostname,
            defaults={
                'system_type': system_info.get('system_type', 'LINUX'),
                'cpu_model': system_info.get('cpu_model', ''),
                'cpu_cores': system_info.get('cpu_cores', 0),
                'ram_total': system_info.get('ram_total', 0),
                'gpu_model': system_info.get('gpu_model', ''),
                'os_version': system_info.get('os_version', ''),
                'ip_address': system_info.get('ip_address'),
                'last_seen': timezone.now(),
                'is_active': True,
            }
        )
        return host
    
    @database_sync_to_async
    def get_host_by_hostname(self, hostname):
        """Get a host by hostname"""
        try:
            return Host.objects.get(hostname=hostname)
        except Host.DoesNotExist:
            return None
    
    @database_sync_to_async
    def update_host_last_seen(self, host):
        """Update a host's last_seen timestamp"""
        host.last_seen = timezone.now()
        host.save(update_fields=['last_seen'])
        return host
    
    @database_sync_to_async
    def update_storage_devices(self, host, storage_devices_data):
        """Update a host's storage devices"""
        # Clear existing storage devices if we're receiving a full update
        existing_ids = []
        
        for device_data in storage_devices_data:
            device, created = StorageDevice.objects.update_or_create(
                host=host,
                name=device_data.get('name'),
                defaults={
                    'device_type': device_data.get('device_type', 'OTHER'),
                    'total_bytes': device_data.get('total_bytes', 0),
                }
            )
            existing_ids.append(device.id)
        
        # Remove any devices that weren't in the update
        StorageDevice.objects.filter(host=host).exclude(id__in=existing_ids).delete()
    
    @database_sync_to_async
    def update_network_interfaces(self, host, network_interfaces_data):
        """Update a host's network interfaces"""
        # Clear existing network interfaces if we're receiving a full update
        existing_ids = []
        
        for interface_data in network_interfaces_data:
            interface, created = NetworkInterface.objects.update_or_create(
                host=host,
                name=interface_data.get('name'),
                defaults={
                    'mac_address': interface_data.get('mac_address', ''),
                    'ip_address': interface_data.get('ip_address'),
                    'is_up': interface_data.get('is_up', True),
                }
            )
            existing_ids.append(interface.id)
        
        # Remove any interfaces that weren't in the update
        NetworkInterface.objects.filter(host=host).exclude(id__in=existing_ids).delete()
    
    @database_sync_to_async
    def store_metric(self, host, metric_name, value_data, timestamp):
        """Store a metric value"""
        # Get or create the metric type
        category = value_data.get('category', 'OTHER')
        unit = value_data.get('unit', '')
        data_type = value_data.get('data_type', 'FLOAT')
        
        metric_type, _ = MetricType.objects.get_or_create(
            name=metric_name,
            defaults={
                'description': f'Auto-created metric for {metric_name}',
                'unit': unit,
                'data_type': data_type,
                'category': category,
            }
        )
        
        # Create the metric value
        value = value_data.get('value')
        metric_value = MetricValue(
            host=host,
            metric_type=metric_type,
            timestamp=timestamp,
        )
        
        # Set the appropriate value field based on data type
        if data_type == 'FLOAT':
            metric_value.float_value = float(value) if value is not None else None
        elif data_type == 'INT':
            metric_value.int_value = int(value) if value is not None else None
        elif data_type == 'STR':
            metric_value.str_value = str(value) if value is not None else None
        elif data_type == 'BOOL':
            metric_value.bool_value = bool(value) if value is not None else None
        
        # Set context references if provided
        storage_device_name = value_data.get('storage_device')
        if storage_device_name:
            try:
                metric_value.storage_device = StorageDevice.objects.get(
                    host=host, name=storage_device_name
                )
            except StorageDevice.DoesNotExist:
                pass
        
        network_interface_name = value_data.get('network_interface')
        if network_interface_name:
            try:
                metric_value.network_interface = NetworkInterface.objects.get(
                    host=host, name=network_interface_name
                )
            except NetworkInterface.DoesNotExist:
                pass
        
        metric_value.save()
        return metric_value