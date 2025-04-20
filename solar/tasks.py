from datetime import timedelta
from django.utils import timezone
from django.db import transaction
from .models import SolarControllerData

def cleanup_old_solar_data(days=7):
    """
    Clean up solar data older than the specified number of days.
    This should be run as a scheduled task.
    """
    cutoff_date = timezone.now() - timedelta(days=days)
    
    with transaction.atomic():
        old_records = SolarControllerData.objects.filter(timestamp__lt=cutoff_date)
        count = old_records.count()
        old_records.delete()
        
    return count
