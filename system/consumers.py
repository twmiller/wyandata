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
        
        # Log registration event onlyed
        print(f"REGISTRATION: Host {hostname} registered from {self.client_addr}")
        if client_id:
        # Create or update host record and related data
        host = await self.update_host_record(
            hostname,         import uuid
            data.get('system_info', {}),(client_id)
            client_id=data.get('client_id'),
            short_name=data.get('short_name', ''),        # Invalid UUID format, won't use it
            description=data.get('description', '') client_id format from {hostname}, ignoring: {client_id}")
        )
        
        if 'storage_devices' in data:nt only
            await self.update_storage_devices(host, data['storage_devices'])registered from {self.client_addr}" + 
         if client_id else ""))
        if 'network_interfaces' in data:
            await self.update_network_interfaces(host, data['network_interfaces'])ata
        
        # Confirm registration                                  client_id, 
        await self.send(text_data=json.dumps({                                     data.get('short_name', ''),
            'type': 'registration_confirmed', ''))
            'host_id': str(host.id),
            'timestamp': timezone.now().isoformat(),
            'message': 'Host registered successfully. Keep the connection open for sending metrics.'await self.update_storage_devices(host, data['storage_devices'])
        }))
        
        # Start the heartbeat mechanism to keep the connection alive        await self.update_network_interfaces(host, data['network_interfaces'])
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
            dumps({
        # Create a new heartbeat task with weak reference to avoid holding connectioned',
        self.heartbeat_task = asyncio.create_task(self.send_heartbeat())),
        'timestamp': timezone.now().isoformat(),
    async def handle_metrics_update(self, data): registered successfully. Keep the connection open for sending metrics.'
        """Process incoming metrics from client agents"""
        hostname = data.get('hostname')
        metrics = data.get('metrics', {})
        timestamp = timezone.now()
        cancel()
        # Ensure host exists
        host = await self.get_host_by_hostname(hostname)e a new heartbeat task with weak reference to avoid holding connection
        if not host:beat_task = asyncio.create_task(self.send_heartbeat())
            print(f"ERROR: Metrics rejected - unknown host {hostname}")
            await self.send(text_data=json.dumps({ata):
                'type': 'error',t agents"""
                'message': f'Host {hostname} not registered'hostname = data.get('hostname')
            }))
            return
        
        # Update host's last seen timestamp# Ensure host exists
        await self.update_host_last_seen(host)me(hostname)
        
        # Store metrics without printing detailss rejected - unknown host {hostname}")
        for metric_name, value_data in metrics.items():wait self.send(text_data=json.dumps({
            await self.store_metric(host, metric_name, value_data, timestamp)
        stname} not registered'
        # Broadcast to all connected clients
        await self.channel_layer.group_send(
            self.room_group_name,
            {ate host's last seen timestamp
                'type': 'metrics_message',wait self.update_host_last_seen(host)
                'hostname': hostname,
                'host_id': str(host.id),ls
                'metrics': metrics,cs.items():
                'timestamp': timestamp.isoformat()etric(host, metric_name, value_data, timestamp)
            }
        )ts
        p_send(
        # Also send to the specific host group
        await self.channel_layer.group_send(
            f'host_{host.id}',
            {   'hostname': hostname,
                'type': 'metrics_message',       'host_id': str(host.id),
                'hostname': hostname,            'metrics': metrics,
                'host_id': str(host.id),
                'metrics': metrics,
                'timestamp': timestamp.isoformat()
            }
        )
    channel_layer.group_send(
    async def handle_host_subscription(self, data):
        """Subscribe client to updates for a specific host"""{
        host_id = data.get('host_id')
        me,
        # Add the client to the host-specific groupst.id),
        if host_id:   'metrics': metrics,
            print(f"SUBSCRIPTION: Client {self.client_addr} subscribed to host {host_id}")    'timestamp': timestamp.isoformat()
            
            await self.channel_layer.group_add(
                f'host_{host_id}',
                self.channel_nameandle_host_subscription(self, data):
            )ubscribe client to updates for a specific host"""
            
            await self.send(text_data=json.dumps({
                'type': 'subscription_confirmed',
                'host_id': host_idid:
            }))ddr} subscribed to host {host_id}")
            
            # Send initial metrics data immediately after subscriptiont self.channel_layer.group_add(
            try:t_id}',
                host = await database_sync_to_async(lambda: Host.objects.get(pk=host_id))()
                
                # Get some recent metrics for this host
                metrics = await self.get_host_recent_metrics(host)
                
                if metrics:
                    await self.send(text_data=json.dumps({
                        'type': 'metrics_update',
                        'host_id': host_id,scription
                        'hostname': host.hostname,        try:
                        'timestamp': timezone.now().isoformat(),to_async(lambda: Host.objects.get(pk=host_id))()
                        'metrics': metrics
                    }))this host
            except Exception as e:_metrics(host)
                print(f"ERROR: Sending initial metrics: {e}")            
    
    async def metrics_message(self, event):
        """Send metrics update to WebSocket clients"""            'type': 'metrics_update',
        # Forward the message to the WebSocket 'host_id': host_id,
        await self.send(text_data=json.dumps(event))
    mezone.now().isoformat(),
    async def send_heartbeat(self):        'metrics': metrics
        """Send periodic pings to keep the connection alive"""
        try:
            while True:
                # Wait before sending first heartbeat
                await asyncio.sleep(25)trics_message(self, event):
                
                # Check if connection is still opend the message to the WebSocket
                if not self.channel_name:ata=json.dumps(event))
                    print(f"HEARTBEAT: Stopping for {self.hostname} - connection closed")
                    return
                """
                print(f"HEARTBEAT: Sending to {self.hostname}")
                e True:
                # Send a ping eartbeat
                await self.send(text_data=json.dumps({
                    'type': 'heartbeat',
                    'timestamp': timezone.now().isoformat()
                }))
                ARTBEAT: Stopping for {self.hostname} - connection closed")
                # Wait for the next heartbeat
                await asyncio.sleep(25)            
        except asyncio.CancelledError:BEAT: Sending to {self.hostname}")
            # Task was cancelled - this is expected during disconnect
            print(f"HEARTBEAT: Task cancelled for {self.hostname}")
        except Exception as e:
            print(f"ERROR: Heartbeat for {self.hostname}: {e}")
    mat()
    # Database helper methods
    @database_sync_to_async
    @with_retry(max_retries=5, retry_delay=0.2)
    def update_host_record(self, hostname, system_info, client_id=None, short_name='', description=''):
        """Create or update a host record"""
        # First try to find by client_id if providedsconnect
        host = Noneme}")
        if client_id:
            try:}")
                host = Host.objects.get(client_id=client_id)
                # If hostname changed but client_id matches, update the hostname
                if host.hostname != hostname:_sync_to_async
                    host.hostname = hostname_retry(max_retries=5, retry_delay=0.2)
                    # Other fields will be updated below_record(self, hostname, system_info, client_id=None, short_name='', description=''):
            except Host.DoesNotExist:    """Create or update a host record"""
                # Will create a new host belowt.objects.update_or_create(
                pass
        
        # If not found by client_id, use the traditional update_or_create by hostname    'system_type': system_info.get('system_type', 'LINUX'),
        if not host:l', ''),
            defaults = {em_info.get('cpu_cores', 0),
                'system_type': system_info.get('system_type', 'LINUX'),tal': system_info.get('ram_total', 0),
                'cpu_model': system_info.get('cpu_model', ''),            'gpu_model': system_info.get('gpu_model', ''),
                'cpu_cores': system_info.get('cpu_cores', 0),': system_info.get('os_version', ''),
                'ram_total': system_info.get('ram_total', 0),get('ip_address'),
                'gpu_model': system_info.get('gpu_model', ''),
                'os_version': system_info.get('os_version', ''),
                'ip_address': system_info.get('ip_address'),
                'last_seen': timezone.now(),ort_name': short_name,
                'is_active': True,            'description': description,
                'short_name': short_name,
                'description': description,
            }
            
            # Include client_id in defaults only if providednc
            if client_id:get_host_by_hostname(self, hostname):
                defaults['client_id'] = client_id
                
            host, created = Host.objects.update_or_create(jects.get(hostname=hostname)
                hostname=hostname,
                defaults=defaults
            )
        else:
            # Update the existing host found by client_idst_last_seen(self, host):
            host.system_type = system_info.get('system_type', host.system_type) date a host's last_seen timestamp"""
            host.cpu_model = system_info.get('cpu_model', host.cpu_model)
            host.cpu_cores = system_info.get('cpu_cores', host.cpu_cores)host.save(update_fields=['last_seen'])
            host.ram_total = system_info.get('ram_total', host.ram_total)
            host.gpu_model = system_info.get('gpu_model', host.gpu_model)
            host.os_version = system_info.get('os_version', host.os_version)@database_sync_to_async
            host.ip_address = system_info.get('ip_address', host.ip_address)ces(self, host, storage_devices_data):
            host.last_seen = timezone.now()
            host.is_active = Truee receiving a full update
            host.short_name = short_name or host.short_name
            host.description = description or host.description
            host.save()for device_data in storage_devices_data:
            date_or_create(
        return host
    e_data.get('name'),
    @database_sync_to_async
    def get_host_by_hostname(self, hostname):e_type': device_data.get('device_type', 'OTHER'),
        """Get a host by hostname"""
        try:
            return Host.objects.get(hostname=hostname)
        except Host.DoesNotExist:ing_ids.append(device.id)
            return None
    the update
    @database_sync_to_asyncStorageDevice.objects.filter(host=host).exclude(id__in=existing_ids).delete()
    def update_host_last_seen(self, host):
        """Update a host's last_seen timestamp"""
        host.last_seen = timezone.now()def update_network_interfaces(self, host, network_interfaces_data):
        host.save(update_fields=['last_seen'])network interfaces"""
        return host update
    
    @database_sync_to_async
    def update_storage_devices(self, host, storage_devices_data):
        """Update a host's storage devices"""nterface.objects.update_or_create(
        # Clear existing storage devices if we're receiving a full update
        existing_ids = []        name=interface_data.get('name'),
        
        for device_data in storage_devices_data:ess': interface_data.get('mac_address', ''),
            device, created = StorageDevice.objects.update_or_create(p_address': interface_data.get('ip_address'),
                host=host,
                name=device_data.get('name'),
                defaults={
                    'device_type': device_data.get('device_type', 'OTHER'),face.id)
                    'total_bytes': device_data.get('total_bytes', 0),
                } Remove any interfaces that weren't in the update
            )NetworkInterface.objects.filter(host=host).exclude(id__in=existing_ids).delete()
            existing_ids.append(device.id)
        
        # Remove any devices that weren't in the updatetric_name, value_data, timestamp):
        StorageDevice.objects.filter(host=host).exclude(id__in=existing_ids).delete()ric value"""
    ype
    @database_sync_to_asynct('category', 'OTHER')
    def update_network_interfaces(self, host, network_interfaces_data):nit = value_data.get('unit', '')
        """Update a host's network interfaces"""data_type = value_data.get('data_type', 'FLOAT')
        # Clear existing network interfaces if we're receiving a full update
        existing_ids = []ype.objects.get_or_create(
        
        for interface_data in network_interfaces_data:
            interface, created = NetworkInterface.objects.update_or_create(
                host=host,
                name=interface_data.get('name'),
                defaults={ory,
                    'mac_address': interface_data.get('mac_address', ''),
                    'ip_address': interface_data.get('ip_address'),)
                    'is_up': interface_data.get('is_up', True),
                }
            )'value')
            existing_ids.append(interface.id)alue = MetricValue(
        
        # Remove any interfaces that weren't in the update
        NetworkInterface.objects.filter(host=host).exclude(id__in=existing_ids).delete()tamp=timestamp,
    
    @database_sync_to_async
    def store_metric(self, host, metric_name, value_data, timestamp):# Set the appropriate value field based on data type
        """Store a metric value"""
        # Get or create the metric typeue = float(value) if value is not None else None
        category = value_data.get('category', 'OTHER')a_type == 'INT':
        unit = value_data.get('unit', '')
        data_type = value_data.get('data_type', 'FLOAT')
        c_value.str_value = str(value) if value is not None else None
        metric_type, _ = MetricType.objects.get_or_create(
            name=metric_name,alue.bool_value = bool(value) if value is not None else None
            defaults={
                'description': f'Auto-created metric for {metric_name}',ences if provided
                'unit': unit, = value_data.get('storage_device')
                'data_type': data_type,    if storage_device_name:
                'category': category,
            }torage_device = StorageDevice.objects.get(
        )_name
            )
        # Create the metric value
        value = value_data.get('value')
        metric_value = MetricValue(
            host=host,twork_interface')
            metric_type=metric_type,nterface_name:
            timestamp=timestamp,
        )
               host=host, name=network_interface_name
        # Set the appropriate value field based on data type
        if data_type == 'FLOAT':face.DoesNotExist:
            metric_value.float_value = float(value) if value is not None else None
        elif data_type == 'INT':
            metric_value.int_value = int(value) if value is not None else None
        elif data_type == 'STR':
            metric_value.str_value = str(value) if value is not None else None
        elif data_type == 'BOOL':
            metric_value.bool_value = bool(value) if value is not None else None
        ient"""
        # Set context references if provided
        storage_device_name = value_data.get('storage_device')ions before making new queries
        if storage_device_name:close_old_connections()
            try:
                metric_value.storage_device = StorageDevice.objects.get(
                    host=host, name=storage_device_name
                )'connection_established',
            except StorageDevice.DoesNotExist:    'message': 'Connected to system metrics. Please subscribe to specific hosts.'
                pass
        pt Exception as e:
        network_interface_name = value_data.get('network_interface')
        if network_interface_name:
            try:
                metric_value.network_interface = NetworkInterface.objects.get(ections
                    host=host, name=network_interface_name
                )
            except NetworkInterface.DoesNotExist:nc_to_async
                passtrics(self, host):
        
        metric_value.save()
        return metric_value
    
    @database_sync_to_async
    def get_latest_data(self):pes = MetricType.objects.filter(
        """Fetch the latest data for the client"""    values__host=host
        try:
            # Close any old connections before making new queries
            close_old_connections()
            
            # Return connection established messagemetric_type in metric_types:
            return {for each metric type












































            close_old_connections()        finally:            return {}            print(f"Error fetching host metrics: {e}")        except Exception as e:            return metrics                                }                        'category': metric_type.category                        'timestamp': latest.timestamp.isoformat(),                        'unit': metric_type.unit,                        'value': latest.value,                    metrics[metric_type.name] = {                if latest:                                ).order_by('-timestamp').first()                    metric_type=metric_type                    host=host,                 latest = MetricValue.objects.filter(                # Get latest value for each metric type            for metric_type in metric_types:                        metrics = {}                        ).distinct()                values__host=host            metric_types = MetricType.objects.filter(            # Get distinct metric types for this host                        close_old_connections()        try:        """Get recent metrics for a host"""    def get_host_recent_metrics(self, host):    @database_sync_to_async                close_old_connections()            # Always close connections        finally:            return None            # Handle exceptions        except Exception as e:            }                'message': 'Connected to system metrics. Please subscribe to specific hosts.'                'type': 'connection_established',                latest = MetricValue.objects.filter(
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