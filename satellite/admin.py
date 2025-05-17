from django.contrib import admin
from .models import EMWINFile

@admin.register(EMWINFile)
class EMWINFileAdmin(admin.ModelAdmin):
    list_display = ('filename', 'product_id', 'source_datetime', 'station_id', 'size_bytes', 'has_been_read')
    list_filter = ('product_id', 'station_id', 'has_been_read', 'wmo_header', 'station_country', 'station_state')
    search_fields = ('filename', 'product_id', 'station_id', 'preview', 'station_name', 'station_location')
    date_hierarchy = 'source_datetime'
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('File Information', {
            'fields': ('filename', 'path', 'size_bytes', 'last_modified')
        }),
        ('Metadata', {
            'fields': ('parsed', 'wmo_header', 'originator', 'comm_id', 'message_id', 'version', 'product_id')
        }),
        ('Timing', {
            'fields': ('source_datetime', 'full_timestamp', 'day', 'hour', 'minute')
        }),
        ('Product Information', {
            'fields': ('product_name', 'product_category')
        }),
        ('Station Information', {
            'fields': (
                'station_id', 'station_name', 'station_location', 
                'station_latitude', 'station_longitude', 'station_elevation_meters',
                'station_type', 'station_state', 'station_country'
            ),
            'classes': ('wide',)
        }),
        ('Content', {
            'fields': ('preview', 'content_size_bytes', 'has_been_read')
        }),
        ('System', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    # Add a basic map with the station location if coordinates are available
    def change_view(self, request, object_id, form_url="", extra_context=None):
        extra_context = extra_context or {}
        obj = self.get_object(request, object_id)
        if obj and obj.has_coordinates:
            extra_context['has_map'] = True
        return super().change_view(request, object_id, form_url, extra_context)
