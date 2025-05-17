from django.contrib import admin
from .models import EMWINFile, EMWINStation, EMWINProduct

@admin.register(EMWINStation)
class EMWINStationAdmin(admin.ModelAdmin):
    list_display = ('station_id', 'name', 'location', 'type', 'country', 'state', 'file_count')
    list_filter = ('country', 'state', 'type')
    search_fields = ('station_id', 'name', 'location')
    readonly_fields = ('file_count', 'last_seen', 'first_seen')
    fieldsets = (
        ('Station Information', {
            'fields': ('station_id', 'name', 'location', 'type', 'country', 'state')
        }),
        ('Geographic Data', {
            'fields': ('latitude', 'longitude', 'elevation_meters')
        }),
        ('Activity', {
            'fields': ('first_seen', 'last_seen', 'file_count')
        }),
    )

@admin.register(EMWINProduct)
class EMWINProductAdmin(admin.ModelAdmin):
    list_display = ('product_id', 'name', 'category', 'file_count')
    list_filter = ('category',)
    search_fields = ('product_id', 'name', 'description')
    readonly_fields = ('file_count', 'last_seen', 'first_seen')
    fieldsets = (
        ('Product Information', {
            'fields': ('product_id', 'name', 'category', 'description')
        }),
        ('Activity', {
            'fields': ('first_seen', 'last_seen', 'file_count')
        }),
    )

@admin.register(EMWINFile)
class EMWINFileAdmin(admin.ModelAdmin):
    list_display = ('filename', 'product', 'source_datetime', 'station', 'size_bytes', 'has_been_read')
    list_filter = ('product', 'station', 'has_been_read', 'wmo_header')
    search_fields = ('filename', 'preview')
    date_hierarchy = 'source_datetime'
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('File Information', {
            'fields': ('filename', 'path', 'size_bytes', 'last_modified')
        }),
        ('Metadata', {
            'fields': ('parsed', 'wmo_header', 'originator', 'comm_id', 'message_id', 'version')
        }),
        ('Relations', {
            'fields': ('product', 'station')
        }),
        ('Timing', {
            'fields': ('source_datetime', 'full_timestamp', 'day', 'hour', 'minute')
        }),
        ('Content', {
            'fields': ('preview', 'content_size_bytes', 'has_been_read')
        }),
        ('System', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
