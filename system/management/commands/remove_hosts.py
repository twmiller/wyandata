from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from system.models import Host, MetricValue
import time
import logging

class Command(BaseCommand):
    help = 'Remove hosts and their related data from the system'

    def add_arguments(self, parser):
        parser.add_argument(
            '--hostname',
            type=str,
            help='Hostname of specific host to remove',
        )
        parser.add_argument(
            '--id',
            type=str,
            help='UUID of specific host to remove',
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Remove ALL hosts (use with caution!)',
        )
        parser.add_argument(
            '--inactive',
            action='store_true',
            help='Remove only inactive hosts',
        )
        parser.add_argument(
            '--inactive-days',
            type=int,
            default=7,
            help='Consider hosts inactive if not seen in this many days',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Skip confirmation prompt',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually removing anything',
        )

    def handle(self, *args, **options):
        # Get the hosts to remove based on the options
        hosts_to_remove = self._get_hosts_to_remove(options)
        
        if not hosts_to_remove:
            self.stdout.write(self.style.WARNING('No hosts match the specified criteria.'))
            return
        
        # Show what would be removed
        self._show_hosts_to_remove(hosts_to_remove)
        
        # Handle dry run
        if options['dry_run']:
            self.stdout.write(self.style.SUCCESS('DRY RUN - No changes made.'))
            return
            
        # Get confirmation unless --force is used
        if not options['force'] and not self._confirm_removal(hosts_to_remove):
            self.stdout.write(self.style.SUCCESS('Operation cancelled.'))
            return
            
        # Remove the hosts
        self._remove_hosts(hosts_to_remove)
            
    def _get_hosts_to_remove(self, options):
        """Get the hosts to remove based on the options"""
        if options['hostname']:
            # Remove by hostname
            hosts = Host.objects.filter(hostname=options['hostname'])
            if not hosts.exists():
                self.stdout.write(self.style.ERROR(f"No host found with hostname '{options['hostname']}'"))
                return []
            return hosts
            
        elif options['id']:
            # Remove by UUID
            try:
                host = Host.objects.get(pk=options['id'])
                return [host]
            except Host.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"No host found with ID '{options['id']}'"))
                return []
                
        elif options['inactive']:
            # Remove inactive hosts
            days = options['inactive_days']
            cutoff_date = timezone.now() - timezone.timedelta(days=days)
            hosts = Host.objects.filter(last_seen__lt=cutoff_date)
            return hosts
            
        elif options['all']:
            # Remove all hosts
            return Host.objects.all()
            
        else:
            self.stdout.write(
                self.style.ERROR(
                    'You must specify what to remove: --hostname, --id, --inactive, or --all'
                )
            )
            return []
            
    def _show_hosts_to_remove(self, hosts):
        """Show what would be removed"""
        self.stdout.write(self.style.WARNING(f"The following {hosts.count()} hosts will be removed:"))
        
        for host in hosts:
            # Get counts of related objects
            metrics_count = MetricValue.objects.filter(host=host).count()
            storage_count = host.storage_devices.count()
            network_count = host.network_interfaces.count()
            
            self.stdout.write(
                f"  - {host.hostname} (ID: {host.id})"
            )
            self.stdout.write(
                f"    Last seen: {host.last_seen or 'Never'}"
            )
            self.stdout.write(
                f"    Related data: {metrics_count} metrics, {storage_count} storage devices, "
                f"{network_count} network interfaces"
            )
            
    def _confirm_removal(self, hosts):
        """Get confirmation from the user"""
        self.stdout.write(self.style.WARNING(
            f"\nAre you sure you want to remove {hosts.count()} hosts "
            f"and all their related data? This cannot be undone! [y/N]"
        ))
        
        user_input = input()
        return user_input.lower() == 'y'
            
    def _remove_hosts(self, hosts):
        """Remove the hosts and their related data"""
        start_time = time.time()
        total_hosts = hosts.count()
        total_metrics = 0
        
        for i, host in enumerate(hosts, 1):
            self.stdout.write(f"Removing host {i}/{total_hosts}: {host.hostname}...")
            
            # Count metrics before deletion for reporting
            metrics_count = MetricValue.objects.filter(host=host).count()
            total_metrics += metrics_count
            
            # Delete the host (cascade will handle related objects)
            with transaction.atomic():
                host.delete()
                
            self.stdout.write(
                self.style.SUCCESS(
                    f"  Removed {host.hostname} with {metrics_count} metrics"
                )
            )
            
        # Report completion
        elapsed = time.time() - start_time
        self.stdout.write(
            self.style.SUCCESS(
                f"\nSuccessfully removed {total_hosts} hosts and {total_metrics} metrics "
                f"in {elapsed:.2f} seconds"
            )
        )
