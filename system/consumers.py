# system/consumers.py

import json
import logging
import sys
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from django.db import close_old_connections
from .models import Host, MetricType, MetricValue, StorageDevice, NetworkInterface
from .db_utils import with_retry

# Set up a logger that will definitely output to the console
logger = logging.getLogger('system.consumers')
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.INFO)
formatter = logging.Formatter('SYSTEM: %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)
logger.propagate = False  # Prevent duplicate logs

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
        
        # Send the latest data to the newly connected client
        latest_data = await self.get_latest_data()
        if latest_data:
            await self.send(text_data=json.dumps(latest_data))
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        # Leave the group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
        
        # Close any open database connections
        await database_sync_to_async(close_old_connections)()
    
    async def receive(self, text_data):
        """Handle incoming messages from clients"""
        print(f"SYSTEM WS RECEIVED: {text_data[:100]}")  # Print raw message to stdout
        
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            print(f"SYSTEM MESSAGE TYPE: {message_type} from {data.get('hostname', 'Unknown')}")
            
            if message_type == 'register_host':
                await self.handle_host_registration(data)
            elif message_type == 'metrics_update':
                await self.handle_metrics_update(data)
            elif message_type == 'subscribe_host':
                await self.handle_host_subscription(data)
            else:
                print(f"SYSTEM UNKNOWN MESSAGE TYPE: {message_type}")
        except Exception as e:
            print(f"SYSTEM ERROR PROCESSING MESSAGE: {e}")
    
    async def handle_host_registration(self, data):
        """Register or update a host in the system"""
        hostname = data.get('hostname')
        system_info = data.get('system_info', {})
        
        # Use print for guaranteed output
        print(f"SYSTEM HOST REGISTRATION: {hostname} | {system_info.get('system_type', '?')} | {system_info.get('os_version', '?')}")
        
        # Log the registration directly to stdout
        logger.info(f"Host registered: {hostname} - {system_info.get('system_type', 'unknown')} - "
                    f"{system_info.get('os_version', 'unknown')} - "
                    f"CPU: {system_info.get('cpu_model', 'unknown')[:30]}...")
        
        # Create or update host record
        host = await self.update_host_record(hostname, system_info)
        
        # Update storage devices
        if 'storage_devices' in data:
            storage_count = len(data['storage_devices'])
            total_storage = sum(dev.get('total_bytes', 0) for dev in data['storage_devices'])
            logger.info(f"Host {hostname} storage: {storage_count} devices = "
                       f"{total_storage / (1024**3):.1f} GB")
            await self.update_storage_devices(host, data['storage_devices'])
        
        # Update network interfaces
        if 'network_interfaces' in data:
            interfaces = data['network_interfaces']
            logger.info(f"Host {hostname} reported {len(interfaces)} network interfaces: "
                       f"{', '.join(i.get('name', '?') for i in interfaces)}")
            await self.update_network_interfaces(host, interfaces)
        
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
        
        # Extract only the cpu_usage metric for logging (if it exists)
        if 'cpu_usage' in metrics:
            cpu_value = metrics['cpu_usage'].get('value', 'N/A')
            print(f"SYSTEM: {hostname} CPU_USAGE={cpu_value}%")
        
        # Also log load average which is often a better indicator of system stress
        load_1min = metrics.get('load_avg_1min', {}).get('value', 'N/A')
        mem_percent = metrics.get('memory_percent', {}).get('value', 'N/A')
        
        # Print a concise but informative log line 
        print(f"HOST: {hostname} | CPU: {cpu_value}% | Load: {load_1min} | Memory: {mem_percent}%")
        
        # Ensure host exists
        host = await self.get_host_by_hostname(hostname)
        if not host:
            logger.warning(f"Rejected metrics from unknown host: {hostname}")
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
            # Log the subscription
            logger.info(f"Client subscribed to host: {host_id}")
            
            await self.channel_layer.group_add(
                f'host_{host_id}',
                self.channel_name
            )
            
            await self.send(text_data=json.dumps({
                'type': 'subscription_confirmed',
                'host_id': host_id
            }))
            
            # Send initial metrics data immediately after subscription
            try:
                host = await database_sync_to_async(lambda: Host.objects.get(pk=host_id))()
                
                # Get some recent metrics for this host
                metrics = await self.get_host_recent_metrics(host)
                
                if metrics:
                    await self.send(text_data=json.dumps({
                        'type': 'metrics_update',
                        'host_id': host_id,
                        'hostname': host.hostname,
                        'timestamp': timezone.now().isoformat(),
                        'metrics': metrics
                    }))
            except Exception as e:
                print(f"Error sending initial metrics: {e}")
    
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
    
    @database_sync_to_async
    def get_latest_data(self):
        """Fetch the latest data for the client"""
        try:
            # Close any old connections before making new queries
            close_old_connections()
            
            # Return connection established message
            return {
                'type': 'connection_established',
                'message': 'Connected to system metrics. Please subscribe to specific hosts.'
            }
        except Exception as e:
            # Handle exceptions
            return None
        finally:
            # Always close connections
            close_old_connections()
    
    @database_sync_to_async
    def get_host_recent_metrics(self, host):
        """Get recent metrics for a host"""
        try:
            close_old_connections()
            
            # Get distinct metric types for this host
            metric_types = MetricType.objects.filter(
                values__host=host
            ).distinct()
            
            metrics = {}
            
            for metric_type in metric_types:
                # Get latest value for each metric type
                latest = MetricValue.objects.filter(
                    host=host, 
                    metric_type=metric_type
                ).order_by('-timestamp').first()
                
                if latest:
                    metrics[metric_type.name] = {
                        'value': latest.value,
                        'unit': metric_type.unit,
                        'timestamp': latest.timestamp.isoformat(),
                        'category': metric_type.category
                    }
            
            return metrics
        except Exception as e:
            print(f"Error fetching host metrics: {e}")
            return {}
        finally:
            close_old_connections()