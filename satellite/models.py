from django.db import models
from django.utils import timezone
import os

class EMWINStation(models.Model):
    """Model to store EMWIN station information"""
    station_id = models.CharField(max_length=10, primary_key=True)
    name = models.CharField(max_length=100, null=True, blank=True)
    location = models.CharField(max_length=100, null=True, blank=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    elevation_meters = models.FloatField(null=True, blank=True)
    type = models.CharField(max_length=100, null=True, blank=True)
    state = models.CharField(max_length=2, null=True, blank=True)
    country = models.CharField(max_length=2, null=True, blank=True)
    last_seen = models.DateTimeField(null=True, blank=True)
    first_seen = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = 'EMWIN Station'
        verbose_name_plural = 'EMWIN Stations'
        ordering = ['station_id']
    
    def __str__(self):
        if self.name:
            return f"{self.station_id} - {self.name}"
        return self.station_id
    
    @property
    def has_coordinates(self):
        """Check if the station has coordinates"""
        return self.latitude is not None and self.longitude is not None
    
    @property
    def file_count(self):
        """Return count of files from this station"""
        return self.emwinfiles.count()

class EMWINProduct(models.Model):
    """Model to store EMWIN product information"""
    product_id = models.CharField(max_length=20, primary_key=True)
    name = models.CharField(max_length=100, null=True, blank=True)
    category = models.CharField(max_length=100, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    last_seen = models.DateTimeField(null=True, blank=True)
    first_seen = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = 'EMWIN Product'
        verbose_name_plural = 'EMWIN Products'
        ordering = ['product_id']
    
    def __str__(self):
        if self.name:
            return f"{self.product_id} - {self.name}"
        return self.product_id
    
    @property
    def file_count(self):
        """Return count of files with this product"""
        return self.emwinfiles.count()

class EMWINFile(models.Model):
    """Model to store EMWIN (Emergency Managers Weather Information Network) data files"""
    
    # File information
    filename = models.CharField(max_length=255, unique=True)
    path = models.CharField(max_length=500)
    size_bytes = models.IntegerField()
    last_modified = models.DateTimeField()
    
    # Metadata
    parsed = models.BooleanField(default=False)
    wmo_header = models.CharField(max_length=10, db_index=True)
    originator = models.CharField(max_length=10, db_index=True)
    comm_id = models.CharField(max_length=10)
    message_id = models.CharField(max_length=10)
    version = models.CharField(max_length=5)
    
    # Related models
    product = models.ForeignKey(EMWINProduct, on_delete=models.PROTECT, related_name='emwinfiles')
    station = models.ForeignKey(EMWINStation, on_delete=models.PROTECT, related_name='emwinfiles')
    
    # Timing
    source_datetime = models.DateTimeField(db_index=True)
    full_timestamp = models.DateTimeField()
    day = models.CharField(max_length=2)
    hour = models.CharField(max_length=2)
    minute = models.CharField(max_length=2)
    
    # Content
    preview = models.TextField(null=True, blank=True)
    content_size_bytes = models.IntegerField()
    has_been_read = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-source_datetime']
        indexes = [
            models.Index(fields=['source_datetime', 'product']),
            models.Index(fields=['station', 'product']),
            models.Index(fields=['wmo_header']),
        ]
        verbose_name = 'EMWIN File'
        verbose_name_plural = 'EMWIN Files'
    
    def __str__(self):
        return f"{self.product_id} - {self.filename}"
    
    @property
    def file_extension(self):
        """Return the file extension"""
        _, ext = os.path.splitext(self.filename)
        return ext.lower()
    
    @property
    def is_text_file(self):
        """Check if the file is a text file"""
        return self.file_extension in ['.txt', '.text']
    
    @property
    def is_image_file(self):
        """Check if the file is an image file"""
        return self.file_extension in ['.gif', '.jpg', '.jpeg', '.png']
    
    @property
    def age_in_hours(self):
        """Return the age of the file in hours"""
        delta = timezone.now() - self.source_datetime
        return delta.total_seconds() / 3600
        
    @property
    def product_id(self):
        """Return product ID for backwards compatibility"""
        return self.product.product_id if self.product else None
        
    @property
    def product_name(self):
        """Return product name for backwards compatibility"""
        return self.product.name if self.product else None
        
    @property
    def product_category(self):
        """Return product category for backwards compatibility"""
        return self.product.category if self.product else None
        
    @property
    def station_id(self):
        """Return station ID for backwards compatibility"""
        return self.station.station_id if self.station else None
        
    @property
    def station_name(self):
        """Return station name for backwards compatibility"""
        return self.station.name if self.station else None
        
    @property
    def station_location(self):
        """Return station location for backwards compatibility"""
        return self.station.location if self.station else None
        
    @property
    def station_latitude(self):
        """Return station latitude for backwards compatibility"""
        return self.station.latitude if self.station else None
        
    @property
    def station_longitude(self):
        """Return station longitude for backwards compatibility"""
        return self.station.longitude if self.station else None
        
    @property
    def station_elevation_meters(self):
        """Return station elevation for backwards compatibility"""
        return self.station.elevation_meters if self.station else None
        
    @property
    def station_type(self):
        """Return station type for backwards compatibility"""
        return self.station.type if self.station else None
        
    @property
    def station_state(self):
        """Return station state for backwards compatibility"""
        return self.station.state if self.station else None
        
    @property
    def station_country(self):
        """Return station country for backwards compatibility"""
        return self.station.country if self.station else None
        
    @property
    def has_coordinates(self):
        """Check if the station has coordinates"""
        return self.station and self.station.has_coordinates
