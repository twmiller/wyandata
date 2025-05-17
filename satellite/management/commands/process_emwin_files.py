import os
import re
from datetime import datetime
import pytz
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from satellite.models import EMWINFile, EMWINStation, EMWINProduct

class Command(BaseCommand):
    help = 'Process EMWIN files into the database'

    def add_arguments(self, parser):
        parser.add_argument('directory', type=str, help='Directory containing EMWIN files')
        parser.add_argument('--batch-size', type=int, default=1000, help='Batch size for database inserts')
        parser.add_argument('--preview-length', type=int, default=100, help='Length of content preview')

    def parse_emwin_filename(self, filename):
        """Parse EMWIN filename to extract metadata"""
        # The pattern should match: A_ABCN01KWBC170115_C_KWIN_20250517011502_321540-2-STPTPTCN.TXT
        pattern = r'A_([A-Z0-9]+)([A-Z0-9]{4})(\d{6})_C_([A-Z0-9]+)_(\d{14})_([0-9-]+)-(\d+)-([A-Z0-9]+)\.TXT'
        match = re.match(pattern, filename)
        if not match:
            return None
            
        wmo_header = match.group(1)
        originator = match.group(2)  # This should be the proper station ID (e.g., KWBC)
        date_code = match.group(3)  # DDHHMI format
        comm_id = match.group(4)
        timestamp = match.group(5)  # YYYYMMDDHHmmss format
        message_id = match.group(6)
        version = match.group(7)
        product_id = match.group(8)
        
        # Parse timestamp
        try:
            year = int(timestamp[0:4])
            month = int(timestamp[4:6])
            day = int(timestamp[6:8])
            hour = int(timestamp[8:10])
            minute = int(timestamp[10:12])
            second = int(timestamp[12:14])
            full_timestamp = datetime(year, month, day, hour, minute, second, tzinfo=pytz.UTC)
            
            # Parse source datetime from date_code
            src_day = date_code[0:2]
            src_hour = date_code[2:4]
            src_minute = date_code[4:6]
            
            # Use the same year and month as the full timestamp
            source_datetime = datetime(year, month, int(src_day), int(src_hour), int(src_minute), 0, tzinfo=pytz.UTC)
        except (ValueError, IndexError):
            # Default to file timestamp if parsing fails
            full_timestamp = timezone.now()
            source_datetime = full_timestamp
            src_day = src_hour = src_minute = "00"
        
        return {
            'wmo_header': wmo_header,
            'originator': originator,  # This is the station ID (e.g., KWBC)
            'comm_id': comm_id,
            'message_id': message_id,
            'version': version, 
            'product_id': product_id,
            'full_timestamp': full_timestamp,
            'source_datetime': source_datetime,
            'day': src_day,
            'hour': src_hour,
            'minute': src_minute
        }
        
    def read_file_preview(self, file_path, length=100):
        """Read the first {length} characters from a file"""
        try:
            with open(file_path, 'r', errors='replace') as f:
                return f.read(length)
        except Exception as e:
            return f"Error reading file: {str(e)}"
    
    def handle(self, *args, **options):
        directory = options['directory']
        batch_size = options['batch_size']
        preview_length = options['preview_length']
        
        self.stdout.write(f"Processing EMWIN files in {directory}")
        
        # Get existing filenames for deduplication
        existing_filenames = set(EMWINFile.objects.values_list('filename', flat=True))
        self.stdout.write(f"Found {len(existing_filenames)} existing files in database")
        
        # Product name/category mapping - now we'll use the database
        product_info = {
            product.product_id: {
                'name': product.name, 
                'category': product.category
            } for product in EMWINProduct.objects.all()
        }
        
        # Station info mapping - now we'll use the database
        station_info = {
            station.station_id: {
                'name': station.name,
                'location': station.location,
                'latitude': station.latitude,
                'longitude': station.longitude,
                'elevation_meters': station.elevation_meters,
                'type': station.type,
                'state': station.state,
                'country': station.country
            } for station in EMWINStation.objects.all()
        }
        
        # Default product/station info for common entries if not in DB
        default_products = {
            'STPTPTCN': {'name': 'Spot Forecast', 'category': 'Forecasts/Analyses', 'description': 'Detailed spot forecasts for specific locations or events.'},
        }
        
        default_stations = {
            'KWBC': {
                'name': 'National Weather Service', 
                'location': 'Washington, DC',
                'latitude': 38.8951,
                'longitude': -77.0364,
                'elevation_meters': 25,
                'type': 'Weather Forecast Office',
                'state': 'DC',
                'country': 'US'
            },
        }
        
        # Process files in batches
        files_to_create = []
        total_processed = 0
        total_new = 0
        skipped_files = 0
        
        for filename in os.listdir(directory):
            if not filename.startswith("A_") or not filename.endswith(".TXT"):
                continue
                
            # Skip if already in database
            if filename in existing_filenames:
                skipped_files += 1
                continue
                
            parsed = self.parse_emwin_filename(filename)
            if not parsed:
                continue
                
            file_path = os.path.join(directory, filename)
            file_stat = os.stat(file_path)
            file_preview = self.read_file_preview(file_path, preview_length)
            
            # Get or create product
            product_id = parsed['product_id']
            now = timezone.now()
            
            try:
                product = EMWINProduct.objects.get(product_id=product_id)
                product.last_seen = now
                product.save(update_fields=['last_seen'])
            except EMWINProduct.DoesNotExist:
                # Create new product
                defaults = {
                    'name': None,
                    'category': None,
                    'description': None,
                    'first_seen': now,
                    'last_seen': now
                }
                
                # Use default info if available
                if product_id in default_products:
                    prod_data = default_products[product_id]
                    defaults['name'] = prod_data.get('name')
                    defaults['category'] = prod_data.get('category')
                    defaults['description'] = prod_data.get('description')
                
                product = EMWINProduct.objects.create(
                    product_id=product_id,
                    **defaults
                )
            
            # Get or create station
            station_id = parsed['originator']
            
            try:
                station = EMWINStation.objects.get(station_id=station_id)
                station.last_seen = now
                station.save(update_fields=['last_seen'])
            except EMWINStation.DoesNotExist:
                # Create new station
                defaults = {
                    'name': None,
                    'location': None,
                    'latitude': None,
                    'longitude': None,
                    'elevation_meters': None,
                    'type': None,
                    'state': None,
                    'country': None,
                    'first_seen': now,
                    'last_seen': now
                }
                
                # Use default info if available
                if station_id in default_stations:
                    stn_data = default_stations[station_id]
                    defaults.update(stn_data)
                
                station = EMWINStation.objects.create(
                    station_id=station_id,
                    **defaults
                )
                
            # Create EMWINFile instance
            emwin_file = EMWINFile(
                filename=filename,
                path=file_path,
                size_bytes=file_stat.st_size,
                last_modified=datetime.fromtimestamp(file_stat.st_mtime).replace(tzinfo=pytz.UTC),
                parsed=True,
                wmo_header=parsed['wmo_header'],
                originator=parsed['originator'],
                comm_id=parsed['comm_id'],
                message_id=parsed['message_id'],
                version=parsed['version'],
                product=product,
                station=station,
                source_datetime=parsed['source_datetime'],
                full_timestamp=parsed['full_timestamp'],
                day=parsed['day'],
                hour=parsed['hour'],
                minute=parsed['minute'],
                preview=file_preview,
                content_size_bytes=file_stat.st_size,
                has_been_read=False
            )
            
            files_to_create.append(emwin_file)
            total_new += 1
            
            # Bulk create when batch size is reached
            if len(files_to_create) >= batch_size:
                with transaction.atomic():
                    EMWINFile.objects.bulk_create(files_to_create)
                self.stdout.write(f"Added {len(files_to_create)} files to database")
                files_to_create = []
            
            total_processed += 1
            if total_processed % 10000 == 0:
                self.stdout.write(f"Processed {total_processed} files, added {total_new} new ones, skipped {skipped_files}...")
        
        # Create any remaining files
        if files_to_create:
            with transaction.atomic():
                EMWINFile.objects.bulk_create(files_to_create)
            self.stdout.write(f"Added final {len(files_to_create)} files to database")
            
        self.stdout.write(self.style.SUCCESS(
            f"Successfully processed {total_processed} files. "
            f"Added {total_new} new files to database. "
            f"Skipped {skipped_files} existing files."
        ))
