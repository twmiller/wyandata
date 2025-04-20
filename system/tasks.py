from datetime import timedelta
from django.utils import timezone
from django.db import transaction
from .models import SystemMetrics, ProcessMetrics, NetworkMetrics, SystemInfo

def cleanup_old_system_metrics(hours=6):
    """
    Clean up system monitoring metrics older than the specified number of hours.
    This preserves the basic system information records.
    """
    cutoff_date = timezone.now() - timedelta(hours=hours)
    
    metrics_deleted = 0
    
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
        
        metrics_deleted = system_count + process_count + network_count
    
    return metrics_deleted
