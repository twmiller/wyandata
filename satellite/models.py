from django.db import models
from django.utils import timezone
import os

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
    product_id = models.CharField(max_length=20, db_index=True)
    
    # Timing
    source_datetime = models.DateTimeField(db_index=True)
    full_timestamp = models.DateTimeField()
    day = models.CharField(max_length=2)
    hour = models.CharField(max_length=2)
    minute = models.CharField(max_length=2)
    
    # Product information
    product_name = models.CharField(max_length=100, null=True, blank=True)
    product_category = models.CharField(max_length=100, null=True, blank=True)
    
    # Station information
    station_id = models.CharField(max_length=10, db_index=True)
    station_name = models.CharField(max_length=100, null=True, blank=True)
    station_location = models.CharField(max_length=100, null=True, blank=True)
    station_latitude = models.FloatField(null=True, blank=True)
    station_longitude = models.FloatField(null=True, blank=True)
    station_elevation_meters = models.FloatField(null=True, blank=True)
    station_type = models.CharField(max_length=100, null=True, blank=True)
    station_state = models.CharField(max_length=2, null=True, blank=True)
    station_country = models.CharField(max_length=2, null=True, blank=True)
    
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
            models.Index(fields=['source_datetime', 'product_id']),
            models.Index(fields=['station_id', 'product_id']),
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
    def has_coordinates(self):
        """Check if the station has coordinates"""
        return self.station_latitude is not None and self.station_longitude is not None
