from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from system.models import MetricValue, Host
import logging
import time

class Command(BaseCommand):
    help = 'Flush all system metrics data while preserving host records'

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Confirm that you want to delete all metrics data',
        )
        parser.add_argument(
            '--host',
            type=str,
            help='Optional hostname to target a specific host only',
        )
        parser.add_argument(
            '--older-than',
            type=int,
            help='Delete metrics older than specified days',
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=10000,
            help='Number of records to delete in each batch',
        )

    def handle(self, *args, **options):
        if not options['confirm']:
            self.stdout.write(
                self.style.WARNING('This command will delete ALL metrics data. '
                                  'Use --confirm to proceed.')
            )
            return

        start_time = time.time()
        total_deleted = 0
        hosts = Host.objects.all()
        host_filter = {}

        # Apply host filter if specified
        if options['host']:
            hosts = hosts.filter(hostname=options['host'])
            if not hosts.exists():
                self.stdout.write(
                    self.style.ERROR(f"No host found with hostname '{options['host']}'")
                )
                return
            host_filter['host__in'] = hosts
            self.stdout.write(
                self.style.WARNING(f"Targeting only host: {options['host']}")
            )

        # Apply date filter if specified
        if options['older_than']:
            days = options['older_than']
            cutoff_date = timezone.now() - timezone.timedelta(days=days)
            host_filter['timestamp__lt'] = cutoff_date
            self.stdout.write(
                self.style.WARNING(f"Deleting metrics older than {days} days")
            )

        # Get count before deletion
        total_metrics = MetricValue.objects.filter(**host_filter).count()
        
        self.stdout.write(
            self.style.WARNING(f"Found {total_metrics} metrics records to delete.")
        )
        
        batch_size = options['batch_size']
        
        # Perform deletion in batches to avoid memory issues
        with transaction.atomic():
            while True:
                # Get the IDs for the batch
                ids_to_delete = list(MetricValue.objects.filter(**host_filter)
                                    .values_list('id', flat=True)[:batch_size])
                
                if not ids_to_delete:
                    break
                
                # Delete the batch
                delete_count = MetricValue.objects.filter(id__in=ids_to_delete).delete()[0]
                total_deleted += delete_count
                
                # Progress report
                elapsed = time.time() - start_time
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Deleted {total_deleted} of {total_metrics} metrics "
                        f"({(total_deleted/total_metrics*100):.1f}%) in {elapsed:.1f} seconds"
                    )
                )
                
                # Small pause to allow other queries to run
                time.sleep(0.1)
        
        # Final report
        elapsed = time.time() - start_time
        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully deleted {total_deleted} metrics records in {elapsed:.1f} seconds"
            )
        )
        
        # Update host stats
        hosts_count = hosts.count()
        self.stdout.write(
            self.style.SUCCESS(f"Host records preserved: {hosts_count}")
        )
