import asyncio
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
        # Print connection details for debugging
        client_addr = f"{self.scope['client'][0]}:{self.scope['client'][1]}"
        print(f"CONNECTION: Client {client_addr} connected")
        
        # Store client address for logging
        self.client_addr = client_addr
        
        # Store the heartbeat task so we can cancel it later
        self.heartbeat_task = None
        self.hostname = None  # Will be set during registration
        
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
        # Cancel the heartbeat task if it exists
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
            try:
                await self.heartbeat_task
            except asyncio.CancelledError:
                pass  # Expected when canceling
            
        hostname_info = f" ({self.hostname})" if self.hostname else ""
        print(f"DISCONNECTION: Client {self.client_addr}{hostname_info} disconnected with code {close_code}")
        
        # Leave the group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
        
        # Close any open database connections
        await database_sync_to_async(close_old_connections)()
    
    async def receive(self, text_data):
        """Handle incoming messages from clients"""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            hostname = data.get('hostname', 'Unknown')
            
            # Handle different message types properly
            if message_type == 'register_host':
                # This should happen once per host
                await self.handle_host_registration(data)
            elif message_type == 'metrics_update' or message_type == 'metrics':
                # Just log that metrics were received without details
                print(f"METRICS: Received from {hostname}")
                await self.handle_metrics_update(data)
            elif message_type == 'subscribe_host':
                # This is for frontend clients subscribing to updates
                await self.handle_host_subscription(data)
            elif message_type == 'heartbeat_ack':
                # Client acknowledges heartbeat
                print(f"HEARTBEAT: ACK from {hostname}")
            else:
                print(f"UNKNOWN: Message type '{message_type}' from {hostname}")
        except Exception as e:
            print(f"ERROR: Processing message: {e}")
    
    async def handle_host_registration(self, data):
        """Register or update a host in the system"""
        hostname = data.get('hostname')
        self.hostname = hostname  # Store hostname for logging
        
        # Get client_id if provided
        client_id = data.get('client_id')
        short_name = data.get('short_name', '')
        description = data.get('description', '')
        
        # Detailed debug output to see all registration data
        print(f"REGISTRATION DATA: host={hostname}, client_id={client_id}, short_name='{short_name}', description='{description}'")
        
        # Log registration event
        if client_id:
            print(f"REGISTRATION: Host {hostname} registered from {self.client_addr} (client_id: {client_id})")
        else:
            print(f"REGISTRATION: Host {hostname} registered from {self.client_addr}")
        
        # Create or update host record and related data
        host = await self.update_host_record(
            hostname, 
            data.get('system_info', {}),
            client_id=client_id,
            short_name=short_name,
            description=description
        )
        
        # Verify the host record after saving
        saved_host = await self.get_host_by_hostname(hostname)
        if saved_host:
            print(f"HOST SAVED: {hostname} with client_id={saved_host.client_id}, short_name='{saved_host.short_name}', description='{saved_host.description}'")
        
        if 'storage_devices' in data:
            await self.update_storage_devices(host, data['storage_devices'])
        
        if 'network_interfaces' in data:
            await self.update_network_interfaces(host, data['network_interfaces'])
        
        # Confirm registration
        await self.send(text_data=json.dumps({
            'type': 'registration_confirmed',
            'host_id': str(host.id),
            'timestamp': timezone.now().isoformat(),
            'message': 'Host registered successfully. Keep the connection open for sending metrics.'
        }))
        
        # Start the heartbeat mechanism to keep the connection alive
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
        
        # Create a new heartbeat task with weak reference to avoid holding connection
        self.heartbeat_task = asyncio.create_task(self.send_heartbeat())
    
    async def handle_metrics_update(self, data):
        """Process incoming metrics from client agents"""
        hostname = data.get('hostname')
        metrics = data.get('metrics', {})
        timestamp = timezone.now()
        
        # Ensure host exists
        host = await self.get_host_by_hostname(hostname)
        if not host:
            print(f"ERROR: Metrics rejected - unknown host {hostname}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': f'Host {hostname} not registered'
            }))
            return
        
        # Update host's last seen timestamp
        await self.update_host_last_seen(host)
        
        # Store metrics without printing details
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
            print(f"SUBSCRIPTION: Client {self.client_addr} subscribed to host {host_id}")
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
                print(f"ERROR: Sending initial metrics: {e}")            
                
    async def metrics_message(self, event):
        """Send metrics update to WebSocket clients"""
        # Forward the message to the WebSocket
        await self.send(text_data=json.dumps(event))
    
    async def send_heartbeat(self):
        """Send periodic pings to keep the connection alive"""
        try:
            while True:
                # Wait before sending first heartbeat
                await asyncio.sleep(25)
                
                # Check if connection is still open
                if not self.channel_name:
                    print(f"HEARTBEAT: Stopping for {self.hostname} - connection closed")
                    return
                
                print(f"HEARTBEAT: Sending to {self.hostname}")
                
                # Send a ping
                await self.send(text_data=json.dumps({
                    'type': 'heartbeat',
                    'timestamp': timezone.now().isoformat()
                }))
                
                # Wait for the next heartbeat
                await asyncio.sleep(25)            
        except asyncio.CancelledError:
            # Task was cancelled - this is expected during disconnect
            print(f"HEARTBEAT: Task cancelled for {self.hostname}")
        except Exception as e:
            print(f"ERROR: Heartbeat for {self.hostname}: {e}")
    
    # Database helper methods
    @database_sync_to_async
    @with_retry(max_retries=5, retry_delay=0.2)
    def update_host_record(self, hostname, system_info, client_id=None, short_name='', description=''):
        """Create or update a host record"""       
        # First try to find by client_id if provided
        host = None
        
        # Better handling of client_id
        if client_id:
            # Log the client_id we're trying to use
            print(f"LOOKING UP HOST: {hostname} by client_id={client_id}")
            
            # Validate client_id is proper UUID format
            try:
                import uuid
                # Try to parse the UUID to validate it
                uuid_obj = uuid.UUID(str(client_id))
                
                try:
                    host = Host.objects.get(client_id=uuid_obj)
                    print(f"HOST FOUND: {hostname} by client_id={client_id}")
                    
                    # If hostname changed but client_id matches, update the hostname
                    if host.hostname != hostname:
                        print(f"UPDATING HOSTNAME: from {host.hostname} to {hostname} for client_id={client_id}")
                        host.hostname = hostname
                        # Other fields will be updated below
                except Host.DoesNotExist:
                    print(f"NO HOST FOUND: for client_id={client_id}, will create new host")
                    # Will create a new host below
                    pass
            except (ValueError, TypeError) as e:
                print(f"INVALID CLIENT_ID: {client_id} for host {hostname}: {e}")
                client_id = None  # Don't use invalid client_id
        
        # If not found by client_id, use the traditional update_or_create by hostname
        if not host:
            defaults = {
                'system_type': system_info.get('system_type', 'LINUX'),
                'cpu_model': system_info.get('cpu_model', ''),
                'cpu_cores': system_info.get('cpu_cores', 0),
                'ram_total': system_info.get('ram_total', 0),
                'gpu_model': system_info.get('gpu_model', ''),
                'os_version': system_info.get('os_version', ''),
                'ip_address': system_info.get('ip_address'),
                'last_seen': timezone.now(),
                'is_active': True,
                'short_name': short_name,
                'description': description,
            }
            
            # Include client_id in defaults only if provided
            if client_id:
                defaults['client_id'] = client_id
            
            host, created = Host.objects.update_or_create(
                hostname=hostname,
                defaults=defaults
            )
        else:
            # Update the existing host found by client_id
            host.system_type = system_info.get('system_type', host.system_type)
            host.cpu_model = system_info.get('cpu_model', host.cpu_model)
            host.cpu_cores = system_info.get('cpu_cores', host.cpu_cores)
            host.ram_total = system_info.get('ram_total', host.ram_total)
            host.gpu_model = system_info.get('gpu_model', host.gpu_model)
            host.os_version = system_info.get('os_version', host.os_version)
            host.ip_address = system_info.get('ip_address', host.ip_address)
            host.last_seen = timezone.now()
            host.is_active = True
            host.short_name = short_name or host.short_name
            host.description = description or host.description
            host.save()
        
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
            return None
        finally:
            close_old_connections()
    
    @database_sync_to_async
    def get_host_recent_metrics(self, host):
        """Get recent metrics for a host"""
        try:
            # Close any old connections before making new queries
            close_old_connections()
            
            # Get distinct metric types for this host
            metric_types = MetricType.objects.filter(
                values__host=host
            ).distinct()
            
            metrics = {}
            
            # Get latest value for each metric type
            for metric_type in metric_types:
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