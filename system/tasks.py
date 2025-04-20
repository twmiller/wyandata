from datetime import timedelta
from django.utils import timezone
from django.db import transaction
from .models import SystemMetrics, ProcessMetrics, NetworkMetrics

def cleanup_old_system_data(days=7):
    """
    Clean up system monitoring data older than the specified number of days.
    This should be run as a scheduled task.
    """
    cutoff_date = timezone.now() - timedelta(days=days)
    
    with transaction.atomic():
        # Clean up system metrics
        old_system_metrics = SystemMetrics.objects.filter(timestamp__lt=cutoff_date)
        system_count = old_system_metrics.count()
        old_system_metrics.delete()
        
        # Clean up process metrics
        old_process_metrics = ProcessMetrics.objects.filter(timestamp__lt=cutoff_date)
        process_count = old_process_metrics.count()
        old_process_metrics.delete()
        
        # Clean up network metrics
        old_network_metrics = NetworkMetrics.objects.filter(timestamp__lt=cutoff_date)
        network_count = old_network_metrics.count()
        old_network_metrics.delete()
    
    total_count = system_count + process_count + network_count
    return total_count
