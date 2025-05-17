import os
import re
from datetime import datetime
import pytz
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from satellite.models import EMWINFile

class Command(BaseCommand):
    help = 'Process EMWIN files into the database'

    def add_arguments(self, parser):
        parser.add_argument('directory', type=str, help='Directory containing EMWIN files')
        parser.add_argument('--batch-size', type=int, default=1000, help='Batch size for database inserts')
        parser.add_argument('--preview-length', type=int, default=100, help='Length of content preview')

    def parse_emwin_filename(self, filename):
        """Parse EMWIN filename to extract metadata"""
        pattern = r'A_([A-Z0-9]+)([A-Z0-9]+)(\d{6})_C_([A-Z0-9]+)_(\d{14})_([0-9-]+)-(\d+)-([A-Z0-9]+)\.TXT'
        match = re.match(pattern, filename)
        if not match:
            return None
            
        wmo_header = match.group(1)
        originator = match.group(2)
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
            'originator': originator,
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
        
        # Product name/category mapping - could be extended based on actual data
        product_info = {
            'STPTPTCN': {'name': 'Spot Forecast', 'category': 'Forecasts/Analyses'},
            # Add more known product mappings here
        }
        
        # Station info mapping - could be extended or moved to a separate file
        station_info = {
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
            # Add more station information here
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
            
            # Get product info if available
            product_name = product_category = None
            if parsed['product_id'] in product_info:
                product_name = product_info[parsed['product_id']]['name']
                product_category = product_info[parsed['product_id']]['category']
            
            # Get station info if available
            station_name = station_location = None
            station_lat = station_lon = station_elev = None
            station_type = station_state = station_country = None
            
            if parsed['originator'] in station_info:
                station_data = station_info[parsed['originator']]
                station_name = station_data.get('name')
                station_location = station_data.get('location')
                station_lat = station_data.get('latitude')
                station_lon = station_data.get('longitude')
                station_elev = station_data.get('elevation_meters')
                station_type = station_data.get('type')
                station_state = station_data.get('state')
                station_country = station_data.get('country')
                
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
                product_id=parsed['product_id'],
                source_datetime=parsed['source_datetime'],
                full_timestamp=parsed['full_timestamp'],
                day=parsed['day'],
                hour=parsed['hour'],
                minute=parsed['minute'],
                product_name=product_name,
                product_category=product_category,
                station_id=parsed['originator'],
                station_name=station_name,
                station_location=station_location,
                station_latitude=station_lat,
                station_longitude=station_lon,
                station_elevation_meters=station_elev,
                station_type=station_type,
                station_state=station_state,
                station_country=station_country,
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
