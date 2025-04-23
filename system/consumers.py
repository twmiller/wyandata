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
        # Print connection details for debugging
        print(f"SYSTEM WEBSOCKET CONNECT: Client connected from {self.scope['client']}")
        
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
        # Print disconnection details for debugging
        print(f"SYSTEM WEBSOCKET DISCONNECT: Client {self.scope['client']} disconnected with code: {close_code}")
        
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
            
            # Print receiving type for debugging
            print(f"SYSTEM RECEIVED: {message_type} from {data.get('hostname', 'Unknown')}")
            
            # Handle different message types properly
            if message_type == 'register_host':
                # This should happen once per host
                await self.handle_host_registration(data)
            elif message_type == 'metrics_update' or message_type == 'metrics':
                # This should be the regular metrics update stream 
                # Fix to handle both 'metrics_update' and just 'metrics' type
                await self.handle_metrics_update(data)
            elif message_type == 'subscribe_host':
                # This is for frontend clients subscribing to updates
                await self.handle_host_subscription(data)
            else:
                print(f"SYSTEM UNKNOWN MESSAGE TYPE: {message_type}")
        except Exception as e:
            print(f"SYSTEM ERROR PROCESSING MESSAGE: {e}")
    
    async def handle_host_registration(self, data):
        """Register or update a host in the system"""
        hostname = data.get('hostname')
        system_info = data.get('system_info', {})
        
        # Use print for guaranteed output including a flag if this is a re-registration
        print(f"SYSTEM REGISTRATION: {hostname} | {system_info.get('system_type', '?')} | {system_info.get('os_version', '?')}")
        
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
        
        # Confirm registration but DON'T close the connection
        # Just send a confirmation message with the host_id
        await self.send(text_data=json.dumps({
            'type': 'registration_confirmed',
            'host_id': str(host.id),
            'timestamp': timezone.now().isoformat(),
            'message': 'Host registered successfully. Keep the connection open for sending metrics.'
        }))
        tname} - CONNECTION KEPT OPEN")
        print(f"SYSTEM: Confirmed registration for {hostname} - CONNECTION KEPT OPEN")
        async def handle_metrics_update(self, data):    
        # Return here to ensure we don't fall through to any other codeagents"""rough to any other code
        return
    })
    async def handle_metrics_update(self, data):
        """Process incoming metrics from client agents"""
        hostname = data.get('hostname')# Extract only the cpu_usage metric for logging (if it exists)hostname = data.get('hostname')
        metrics = data.get('metrics', {})
        timestamp = timezone.now()pu_usage'].get('value', 'N/A')
        
        # Extract only the cpu_usage metric for logging (if it exists)
        cpu_value = 'N/A'# Also log load average which is often a better indicator of system stressif 'cpu_usage' in metrics:
        if 'cpu_usage' in metrics:
            cpu_value = metrics['cpu_usage'].get('value', 'N/A')
            print(f"SYSTEM: {hostname} CPU_USAGE={cpu_value}%")
        # Print a concise but informative log line # Also log load average which is often a better indicator of system stress
        # Also log load average which is often a better indicator of system stress% | Load: {load_1min} | Memory: {mem_percent}%")).get('value', 'N/A')
        load_1min = metrics.get('load_avg_1min', {}).get('value', 'N/A')
        mem_percent = metrics.get('memory_percent', {}).get('value', 'N/A')# Ensure host exists
        t_host_by_hostname(hostname)t informative log line 
        # Print a concise but informative log line 
        print(f"HOST: {hostname} | CPU: {cpu_value}% | Load: {load_1min} | Memory: {mem_percent}%")ning(f"Rejected metrics from unknown host: {hostname}")
        
        # Ensure host exists
        host = await self.get_host_by_hostname(hostname)t {hostname} not registered'
        if not host:
            logger.warning(f"Rejected metrics from unknown host: {hostname}")urnit self.send(text_data=json.dumps({
            await self.send(text_data=json.dumps({or',
                'type': 'error',# Update host's last seen timestamp        'message': f'Host {hostname} not registered'
                'message': f'Host {hostname} not registered'
            }))
            return# Store metrics
        , value_data in metrics.items(): last seen timestamp
        # Update host's last seen timestamp
        await self.update_host_last_seen(host)
        # Broadcast to all connected clients# Store metrics
        # Store metrics():
        for metric_name, value_data in metrics.items():amp)
            await self.store_metric(host, metric_name, value_data, timestamp)
           'type': 'metrics_message',adcast to all connected clients
        # Broadcast to all connected clients
        await self.channel_layer.group_send(
            self.room_group_name,
            {amp.isoformat()ssage',
                'type': 'metrics_message',
                'hostname': hostname,host_id': str(host.id),
                'host_id': str(host.id),      'metrics': metrics,
                'metrics': metrics,# Also send to the specific host group        'timestamp': timestamp.isoformat()
                'timestamp': timestamp.isoformat()
            }
        )
           'type': 'metrics_message',o send to the specific host group
        # Also send to the specific host group
        await self.channel_layer.group_send(
            f'host_{host.id}',
            {amp.isoformat()ssage',
                'type': 'metrics_message',
                'hostname': hostname,str(host.id),
                'host_id': str(host.id),  'metrics': metrics,
                'metrics': metrics,async def handle_host_subscription(self, data):            'timestamp': timestamp.isoformat()
                'timestamp': timestamp.isoformat()
            }
        )
    # Add the client to the host-specific groupc def handle_host_subscription(self, data):
    async def handle_host_subscription(self, data):
        """Subscribe client to updates for a specific host"""he subscriptionata.get('host_id')
        host_id = data.get('host_id')ost_id}")
        
        # Add the client to the host-specific groupawait self.channel_layer.group_add(ost_id:
        if host_id:
            # Log the subscriptionbscribed to host: {host_id}")
            logger.info(f"Client subscribed to host: {host_id}")
            t self.channel_layer.group_add(
            await self.channel_layer.group_add(await self.send(text_data=json.dumps({    f'host_{host_id}',
                f'host_{host_id}',
                self.channel_name
            )
            self.send(text_data=json.dumps({
            await self.send(text_data=json.dumps({# Send initial metrics data immediately after subscription    'type': 'subscription_confirmed',
                'type': 'subscription_confirmed',
                'host_id': host_idhost = await database_sync_to_async(lambda: Host.objects.get(pk=host_id))()
            }))
            # Get some recent metrics for this hostnd initial metrics data immediately after subscription
            # Send initial metrics data immediately after subscription
            try:
                host = await database_sync_to_async(lambda: Host.objects.get(pk=host_id))()if metrics:
                elf.send(text_data=json.dumps({recent metrics for this host
                # Get some recent metrics for this host
                metrics = await self.get_host_recent_metrics(host)
                stname,
                if metrics:
                    await self.send(text_data=json.dumps({
                        'type': 'metrics_update',
                        'host_id': host_id,ption as e: 'hostname': host.hostname,
                        'hostname': host.hostname,ing initial metrics: {e}")': timezone.now().isoformat(),
                        'timestamp': timezone.now().isoformat(),
                        'metrics': metricsasync def metrics_message(self, event):                }))
                    })) clients"""
            except Exception as e:
                print(f"Error sending initial metrics: {e}")
    
    async def metrics_message(self, event):async def heartbeat(self):    """Send metrics update to WebSocket clients"""
        """Send metrics update to WebSocket clients"""connection alive"""
        # Forward the message to the WebSocket
        await self.send(text_data=json.dumps(event))
    e.now().isoformat()
    async def heartbeat(self):
        """Send periodic heartbeat messages to keep the connection alive""".send(text_data=json.dumps({
        await self.send(text_data=json.dumps({# Database helper methods        'type': 'heartbeat',
            'type': 'heartbeat',ne.now().isoformat()
            'timestamp': timezone.now().isoformat()etry_delay=0.2)
        }))em_info):
    
    # Database helper methodsor_create(
    @database_sync_to_async
    @with_retry(max_retries=5, retry_delay=0.2)ame, system_info):
    def update_host_record(self, hostname, system_info):m_type': system_info.get('system_type', 'LINUX'),pdate a host record"""
        """Create or update a host record"""
        host, created = Host.objects.update_or_create(
            hostname=hostname,
            defaults={
                'system_type': system_info.get('system_type', 'LINUX'),
                'cpu_model': system_info.get('cpu_model', ''),
                'cpu_cores': system_info.get('cpu_cores', 0),
                'ram_total': system_info.get('ram_total', 0),
                'gpu_model': system_info.get('gpu_model', ''),on', ''),
                'os_version': system_info.get('os_version', ''),ip_address': system_info.get('ip_address'),
                'ip_address': system_info.get('ip_address'),eturn host       'last_seen': timezone.now(),
                'last_seen': timezone.now(),
                'is_active': True,@database_sync_to_async        }
            }lf, hostname):
        )
        return host
    return Host.objects.get(hostname=hostname)e_sync_to_async
    @database_sync_to_async
    def get_host_by_hostname(self, hostname):
        """Get a host by hostname"""
        try:@database_sync_to_async        return Host.objects.get(hostname=hostname)
            return Host.objects.get(hostname=hostname)
        except Host.DoesNotExist:
            return None
    seen'])
    @database_sync_to_async
    def update_host_last_seen(self, host):en timestamp"""
        """Update a host's last_seen timestamp"""@database_sync_to_async    host.last_seen = timezone.now()
        host.last_seen = timezone.now()ces(self, host, storage_devices_data):elds=['last_seen'])
        host.save(update_fields=['last_seen'])
        return hostll update
    
    @database_sync_to_async storage_devices_data):
    def update_storage_devices(self, host, storage_devices_data):for device_data in storage_devices_data:"""Update a host's storage devices"""
        """Update a host's storage devices"""cts.update_or_create(e receiving a full update
        # Clear existing storage devices if we're receiving a full update
        existing_ids = []ame'),
        
        for device_data in storage_devices_data:ta.get('device_type', 'OTHER'),objects.update_or_create(
            device, created = StorageDevice.objects.update_or_create(
                host=host,
                name=device_data.get('name'),
                defaults={xisting_ids.append(device.id)       'device_type': device_data.get('device_type', 'OTHER'),
                    'device_type': device_data.get('device_type', 'OTHER'),
                    'total_bytes': device_data.get('total_bytes', 0),# Remove any devices that weren't in the update        }
                }(id__in=existing_ids).delete()
            )
            existing_ids.append(device.id)@database_sync_to_async    
        rfaces(self, host, network_interfaces_data):s that weren't in the update
        # Remove any devices that weren't in the update
        StorageDevice.objects.filter(host=host).exclude(id__in=existing_ids).delete()update
    
    @database_sync_to_asyncst, network_interfaces_data):
    def update_network_interfaces(self, host, network_interfaces_data):for interface_data in network_interfaces_data:"""Update a host's network interfaces"""
        """Update a host's network interfaces"""cts.update_or_create(eceiving a full update
        # Clear existing network interfaces if we're receiving a full update
        existing_ids = [].get('name'),
        
        for interface_data in network_interfaces_data:ddress': interface_data.get('mac_address', ''),ated = NetworkInterface.objects.update_or_create(
            interface, created = NetworkInterface.objects.update_or_create(
                host=host,
                name=interface_data.get('name'),
                defaults={ta.get('mac_address', ''),
                    'mac_address': interface_data.get('mac_address', ''),xisting_ids.append(interface.id)       'ip_address': interface_data.get('ip_address'),
                    'ip_address': interface_data.get('ip_address'),
                    'is_up': interface_data.get('is_up', True),# Remove any interfaces that weren't in the update        }
                }s).delete()
            )
            existing_ids.append(interface.id)@database_sync_to_async    
        host, metric_name, value_data, timestamp):aces that weren't in the update
        # Remove any interfaces that weren't in the update
        NetworkInterface.objects.filter(host=host).exclude(id__in=existing_ids).delete() type
    HER')
    @database_sync_to_async
    def store_metric(self, host, metric_name, value_data, timestamp):type', 'FLOAT')
        """Store a metric value"""
        # Get or create the metric typemetric_type, _ = MetricType.objects.get_or_create(category = value_data.get('category', 'OTHER')
        category = value_data.get('category', 'OTHER')
        unit = value_data.get('unit', '')
        data_type = value_data.get('data_type', 'FLOAT')to-created metric for {metric_name}',
        
        metric_type, _ = MetricType.objects.get_or_create(data_type,
            name=metric_name,
            defaults={name}',
                'description': f'Auto-created metric for {metric_name}',unit': unit,
                'unit': unit,      'data_type': data_type,
                'data_type': data_type,# Create the metric value        'category': category,
                'category': category,
            }
        )
        e=metric_type,etric value
        # Create the metric value
        value = value_data.get('value')
        metric_value = MetricValue(  host=host,
            host=host,# Set the appropriate value field based on data type    metric_type=metric_type,
            metric_type=metric_type,
            timestamp=timestamp,alue = float(value) if value is not None else None
        )
         is not None else Nonetype
        # Set the appropriate value field based on data type
        if data_type == 'FLOAT':ue = str(value) if value is not None else Nonealue = float(value) if value is not None else None
            metric_value.float_value = float(value) if value is not None else None
        elif data_type == 'INT':if value is not None else None value is not None else None
            metric_value.int_value = int(value) if value is not None else None
        elif data_type == 'STR':# Set context references if provided    metric_value.str_value = str(value) if value is not None else None
            metric_value.str_value = str(value) if value is not None else None
        elif data_type == 'BOOL':
            metric_value.bool_value = bool(value) if value is not None else None
        alue.storage_device = StorageDevice.objects.get(ferences if provided
        # Set context references if provided
        storage_device_name = value_data.get('storage_device')
        if storage_device_name: StorageDevice.DoesNotExist:
            try:
                metric_value.storage_device = StorageDevice.objects.get(ame=storage_device_name
                    host=host, name=storage_device_namenetwork_interface_name = value_data.get('network_interface')        )
                )
            except StorageDevice.DoesNotExist:
                passalue.network_interface = NetworkInterface.objects.get(
        
        network_interface_name = value_data.get('network_interface')
        if network_interface_name:rface.DoesNotExist:
            try:
                metric_value.network_interface = NetworkInterface.objects.get(ame=network_interface_name
                    host=host, name=network_interface_namemetric_value.save()        )
                )
            except NetworkInterface.DoesNotExist:
                pass@database_sync_to_async    
        
        metric_value.save()ta for the client"""
        return metric_value
    # Close any old connections before making new queriese_sync_to_async
    @database_sync_to_async
    def get_latest_data(self):
        """Fetch the latest data for the client"""# Return connection established message
        try:
            # Close any old connections before making new queriese': 'connection_established',d_connections()
            close_old_connections()fic hosts.'
            
            # Return connection established messaget Exception as e:eturn {
            return {
                'type': 'connection_established', metrics. Please subscribe to specific hosts.'
                'message': 'Connected to system metrics. Please subscribe to specific hosts.'
            }ways close connectionsxception as e:
        except Exception as e:
            # Handle exceptions
            return None@database_sync_to_async    finally:
        finally:rics(self, host):connections
            # Always close connections
            close_old_connections()
    close_old_connections()e_sync_to_async
    @database_sync_to_async
    def get_host_recent_metrics(self, host):# Get distinct metric types for this hostet recent metrics for a host"""
        """Get recent metrics for a host"""
        try:
            close_old_connections()
            pes for this host
            # Get distinct metric types for this hostmetrics = {}metric_types = MetricType.objects.filter(
            metric_types = MetricType.objects.filter(
                values__host=hostfor metric_type in metric_types:).distinct()
            ).distinct()
            
            metrics = {}
            =metric_typemetric_types:
            for metric_type in metric_types:rst() metric type
                # Get latest value for each metric type
                latest = MetricValue.objects.filter(if latest:    host=host, 
                    host=host, ric_type.name] = {=metric_type
                    metric_type=metric_type
                ).order_by('-timestamp').first()
                
                if latest:
                    metrics[metric_type.name] = {
                        'value': latest.value,unit,
                        'unit': metric_type.unit,return metrics            'timestamp': latest.timestamp.isoformat(),
                        'timestamp': latest.timestamp.isoformat(),        except Exception as e:                        'category': metric_type.category
                        'category': metric_type.category            print(f"Error fetching host metrics: {e}")                    }
                    }            return {}            
                    finally:            return metrics
            return metrics            close_old_connections()        except Exception as e:            print(f"Error fetching host metrics: {e}")            return {}        finally:            close_old_connections()