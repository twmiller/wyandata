from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from datetime import datetime, date
from solar.tasks import calculate_daily_aggregate, calculate_monthly_aggregate, calculate_yearly_aggregate, update_total_aggregate

class Command(BaseCommand):
    help = 'Aggregate solar data for various time periods'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--daily',
            action='store_true',
            help='Run daily aggregation',
        )
        parser.add_argument(
            '--monthly',
            action='store_true',
            help='Run monthly aggregation',
        )
        parser.add_argument(
            '--yearly',
            action='store_true',
            help='Run yearly aggregation',
        )
        parser.add_argument(
            '--total',
            action='store_true',
            help='Update total lifetime stats',
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Run all aggregation types',
        )
        parser.add_argument(
            '--date',
            help='Specific date for daily aggregation (YYYY-MM-DD)',
        )
        parser.add_argument(
            '--month',
            help='Specific month for monthly aggregation (YYYY-MM)',
        )
        parser.add_argument(
            '--year',
            type=int,
            help='Specific year for yearly aggregation',
        )
    
    def handle(self, *args, **options):
        if options['all']:
            options['daily'] = options['monthly'] = options['yearly'] = options['total'] = True
            
        if not any([options['daily'], options['monthly'], options['yearly'], options['total']]):
            # Default to all if no specific option provided
            options['daily'] = options['monthly'] = options['yearly'] = options['total'] = True
        
        # Process daily aggregation
        if options['daily']:
            target_date = None
            if options['date']:
                try:
                    target_date = datetime.strptime(options['date'], '%Y-%m-%d').date()
                except ValueError:
                    raise CommandError('Invalid date format. Use YYYY-MM-DD')
            
            result = calculate_daily_aggregate(target_date)
            if result:
                self.stdout.write(self.style.SUCCESS(f'Daily aggregation completed for {result.date}'))
            else:
                self.stdout.write(self.style.WARNING('No data found for daily aggregation'))
        
        # Process monthly aggregation
        if options['monthly']:
            year, month = None, None
            if options['month']:
                try:
                    year_month = datetime.strptime(options['month'], '%Y-%m')
                    year = year_month.year
                    month = year_month.month
                except ValueError:
                    raise CommandError('Invalid month format. Use YYYY-MM')
            
            result = calculate_monthly_aggregate(year, month)
            if result:
                self.stdout.write(self.style.SUCCESS(f'Monthly aggregation completed for {result.year}-{result.month:02d}'))
            else:
                self.stdout.write(self.style.WARNING('No data found for monthly aggregation'))
        
        # Process yearly aggregation
        if options['yearly']:
            year = options['year']
            result = calculate_yearly_aggregate(year)
            if result:
                self.stdout.write(self.style.SUCCESS(f'Yearly aggregation completed for {result.year}'))
            else:
                self.stdout.write(self.style.WARNING('No data found for yearly aggregation'))
        
        # Update total stats
        if options['total']:
            update_total_aggregate()
            self.stdout.write(self.style.SUCCESS('Total lifetime stats updated'))
