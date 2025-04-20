from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from system.tasks import cleanup_old_system_metrics

class Command(BaseCommand):
    help = 'Cleans up old system monitoring metrics data'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--hours',
            type=int,
            default=6,
            help='Delete metrics data older than this many hours (default: 6)',
        )
        
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show how many records would be deleted without actually deleting',
        )
    
    def handle(self, *args, **options):
        hours = options['hours']
        dry_run = options['dry_run']
        
        # Calculate the cutoff date
        cutoff_date = timezone.now() - timedelta(hours=hours)
        
        if dry_run:
            from system.models import SystemMetrics, ProcessMetrics, NetworkMetrics
            system_count = SystemMetrics.objects.filter(timestamp__lt=cutoff_date).count()
            process_count = ProcessMetrics.objects.filter(timestamp__lt=cutoff_date).count()
            network_count = NetworkMetrics.objects.filter(timestamp__lt=cutoff_date).count()
            total_count = system_count + process_count + network_count
            
            self.stdout.write(
                self.style.WARNING(f'Would delete {total_count} metric records older than {cutoff_date.strftime("%Y-%m-%d %H:%M:%S")}:')
            )
            self.stdout.write(self.style.WARNING(f'  - {system_count} system metrics records'))
            self.stdout.write(self.style.WARNING(f'  - {process_count} process metrics records'))
            self.stdout.write(self.style.WARNING(f'  - {network_count} network metrics records'))
            self.stdout.write(self.style.SUCCESS('System identification records would remain intact.'))
        else:
            # Execute the cleanup
            count = cleanup_old_system_metrics(hours)
            self.stdout.write(
                self.style.SUCCESS(f'Successfully deleted {count} system metrics records older than {cutoff_date.strftime("%Y-%m-%d %H:%M:%S")}')
            )
            self.stdout.write(self.style.SUCCESS('System identification records remain intact.'))
