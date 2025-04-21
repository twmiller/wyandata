from django.core.management.base import BaseCommand
from django.utils import timezone
from weather.models import OutdoorWeatherReading, IndoorSensor
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Clean up old weather readings to prevent database bloat'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='Number of days of raw data to keep (default: 7)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Perform a dry run without deleting any data'
        )

    def handle(self, *args, **options):
        days_to_keep = options['days']
        dry_run = options['dry_run']
        
        self.stdout.write(f'Cleaning up weather data older than {days_to_keep} days')
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - no data will be deleted'))
        
        # Calculate the cutoff date
        cutoff_date = timezone.now() - timedelta(days=days_to_keep)
        
        # Process outdoor readings
        outdoor_count = OutdoorWeatherReading.objects.filter(time__lt=cutoff_date).count()
        self.stdout.write(f'Found {outdoor_count} outdoor readings older than {cutoff_date}')
        
        if not dry_run and outdoor_count > 0:
            OutdoorWeatherReading.objects.filter(time__lt=cutoff_date).delete()
            self.stdout.write(self.style.SUCCESS(f'Deleted {outdoor_count} outdoor readings'))
        
        # Process indoor readings
        indoor_count = IndoorSensor.objects.filter(time__lt=cutoff_date).count()
        self.stdout.write(f'Found {indoor_count} indoor readings older than {cutoff_date}')
        
        if not dry_run and indoor_count > 0:
            IndoorSensor.objects.filter(time__lt=cutoff_date).delete()
            self.stdout.write(self.style.SUCCESS(f'Deleted {indoor_count} indoor readings'))
        
        # Summary
        total_removed = outdoor_count + indoor_count
        if dry_run:
            self.stdout.write(self.style.WARNING(f'DRY RUN: Would have removed {total_removed} records'))
        else:
            self.stdout.write(self.style.SUCCESS(f'Cleanup complete. Removed {total_removed} records'))
