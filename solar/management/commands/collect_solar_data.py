import time
import logging
from django.core.management.base import BaseCommand
from solar.models import SolarControllerData
from solar.utils import get_solar_data

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Collect data from the solar charge controller'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--interval',
            type=int,
            default=300,
            help='Interval between data collections in seconds (default: 300)',
        )
        parser.add_argument(
            '--count',
            type=int,
            default=None,
            help='Number of collections to perform (default: run indefinitely)',
        )
    
    def handle(self, *args, **options):
        interval = options['interval']
        count = options['count']
        
        self.stdout.write(self.style.SUCCESS(f'Starting solar data collection every {interval} seconds'))
        
        collections = 0
        try:
            while count is None or collections < count:
                data = get_solar_data()
                
                if data:
                    # Create a new database record
                    solar_data = SolarControllerData(**data)
                    solar_data.save()
                    
                    self.stdout.write(self.style.SUCCESS(
                        f'Collected solar data: {solar_data.pv_array_power}W, {solar_data.battery_voltage}V'
                    ))
                else:
                    self.stdout.write(self.style.WARNING('Failed to collect solar data'))
                
                collections += 1
                
                if count is not None and collections >= count:
                    break
                    
                time.sleep(interval)
                
        except KeyboardInterrupt:
            self.stdout.write(self.style.SUCCESS('Data collection stopped by user'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error during data collection: {e}'))
