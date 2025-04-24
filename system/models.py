# system/models.py

from django.db import models
import uuid
from django.utils import timezone
from datetime import timedelta

class Host(models.Model):
    """Represents a monitored system in the infrastructure"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    client_id = models.UUIDField(unique=True, null=True, blank=True, 
                                 help_text="Client-generated persistent UUID")
    hostname = models.CharField(max_length=255)
    short_name = models.CharField(max_length=100, blank=True, 
                                  help_text="User-friendly short name for this host")
    description = models.TextField(blank=True, 
                                   help_text="Description of this host's purpose or location")
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    system_type = models.CharField(max_length=50, choices=[
        ('LINUX', 'Linux'),
        ('MACOS', 'macOS'),
        ('RASPBERRY', 'Raspberry Pi'),
    ])
    
    # Basic system info
    cpu_model = models.CharField(max_length=255, blank=True)
    cpu_cores = models.IntegerField(default=0)
    ram_total = models.BigIntegerField(default=0)  # Total RAM in bytes
    gpu_model = models.CharField(max_length=255, blank=True)
    os_version = models.CharField(max_length=255, blank=True)
    
    # Status tracking
    last_seen = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    
    @property
    def current_status(self):
        """Calculate the current status based on last_seen time"""
        if not self.last_seen:
            return False
            
        # Consider hosts inactive if not seen in the last hour
        time_since_last_seen = timezone.now() - self.last_seen
        is_active = time_since_last_seen < timedelta(hours=1)
        
        # Debug info to help diagnose
        hours = time_since_last_seen.total_seconds() / 3600
        print(f"DEBUG: Host {self.hostname} last seen {hours:.2f} hours ago, status: {'active' if is_active else 'inactive'}")
        
        return is_active
    
    def __str__(self):
        return f"{self.hostname} ({self.get_system_type_display()})"

class StorageDevice(models.Model):
    """Represents a storage device on a host"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    host = models.ForeignKey(Host, on_delete=models.CASCADE, related_name='storage_devices')
    name = models.CharField(max_length=255)  # Device name or mount point
    device_type = models.CharField(max_length=50, choices=[
        ('SSD', 'SSD'),
        ('HDD', 'HDD'),
        ('NVME', 'NVMe'),
        ('OTHER', 'Other'),
    ], default='OTHER')
    total_bytes = models.BigIntegerField(default=0)
    
    def __str__(self):
        return f"{self.name} on {self.host.hostname}"

class NetworkInterface(models.Model):
    """Represents a network interface on a host"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    host = models.ForeignKey(Host, on_delete=models.CASCADE, related_name='network_interfaces')
    name = models.CharField(max_length=100)  # Interface name
    mac_address = models.CharField(max_length=17, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    is_up = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.name} on {self.host.hostname}"

class MetricType(models.Model):
    """Defines different types of metrics that can be collected"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    unit = models.CharField(max_length=50, blank=True)
    data_type = models.CharField(max_length=20, choices=[
        ('FLOAT', 'Float'),
        ('INT', 'Integer'),
        ('STR', 'String'),
        ('BOOL', 'Boolean'),
    ], default='FLOAT')
    category = models.CharField(max_length=50, choices=[
        ('CPU', 'CPU'),
        ('MEMORY', 'Memory'),
        ('STORAGE', 'Storage'),
        ('NETWORK', 'Network'),
        ('SYSTEM', 'System'),
        ('TEMPERATURE', 'Temperature'),
        ('OTHER', 'Other'),
    ], default='OTHER')
    
    def __str__(self):
        return f"{self.name} ({self.unit})"

class MetricValue(models.Model):
    """Stores time-series metric values for hosts"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    host = models.ForeignKey(Host, on_delete=models.CASCADE, related_name='metrics')
    metric_type = models.ForeignKey(MetricType, on_delete=models.CASCADE, related_name='values')
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    
    # Value fields based on data type
    float_value = models.FloatField(null=True, blank=True)
    int_value = models.BigIntegerField(null=True, blank=True)
    str_value = models.TextField(null=True, blank=True)
    bool_value = models.BooleanField(null=True, blank=True)
    
    # Optional references for context
    storage_device = models.ForeignKey(StorageDevice, on_delete=models.CASCADE, 
                                       related_name='metrics', null=True, blank=True)
    network_interface = models.ForeignKey(NetworkInterface, on_delete=models.CASCADE, 
                                          related_name='metrics', null=True, blank=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['timestamp']),
            models.Index(fields=['host', 'metric_type', 'timestamp']),
        ]
    
    @property
    def value(self):
        """Returns the value based on the metric type's data type"""
        if self.metric_type.data_type == 'FLOAT':
            return self.float_value
        elif self.metric_type.data_type == 'INT':
            return self.int_value
        elif self.metric_type.data_type == 'STR':
            return self.str_value
        elif self.metric_type.data_type == 'BOOL':
            return self.bool_value
        return None