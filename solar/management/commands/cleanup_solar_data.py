from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from solar.models import SolarControllerData


class Command(BaseCommand):
    help = 'Cleans up old solar controller data'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='Delete data older than this many days (default: 7)',
        )
        
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show how many records would be deleted without actually deleting',
        )
    
    def handle(self, *args, **options):
        days = options['days']
        dry_run = options['dry_run']
        
        # Calculate the cutoff date
        cutoff_date = timezone.now() - timedelta(days=days)
        
        # Query for records to delete
        old_records = SolarControllerData.objects.filter(timestamp__lt=cutoff_date)
        count = old_records.count()
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(f'Would delete {count} records older than {cutoff_date.strftime("%Y-%m-%d")}')
            )
        else:
            # Delete the records
            old_records.delete()
            self.stdout.write(
                self.style.SUCCESS(f'Successfully deleted {count} records older than {cutoff_date.strftime("%Y-%m-%d")}')
            )
