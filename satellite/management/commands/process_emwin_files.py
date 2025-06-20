import os
import re
import logging
import requests
import time
from datetime import datetime, timedelta
import pytz
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from django.conf import settings
from satellite.models import EMWINFile, EMWINStation, EMWINProduct
from django.db.models import Count, Q

# Set up logging
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Process EMWIN files into the database'

    def add_arguments(self, parser):
        parser.add_argument('directory', type=str, help='Directory containing EMWIN files')
        parser.add_argument('--batch-size', type=int, default=1000, help='Batch size for database inserts')
        parser.add_argument('--preview-length', type=int, default=100, help='Length of content preview')
        
        # Add clean flag to remove existing records
        parser.add_argument('--clean', action='store_true', help='Remove all existing EMWIN files before importing')
        parser.add_argument('--clean-all', action='store_true', help='Remove all EMWIN files, products, and stations before importing')
        parser.add_argument('--clean-confirm', action='store_true', help='Confirm clean operation without prompting')
        
        # Add station lookup options
        parser.add_argument('--lookup-stations', action='store_true', help='Try to fetch station information from external APIs')
        parser.add_argument('--lookup-missing-only', action='store_true', help='Only look up stations with missing information')
        parser.add_argument('--lookup-timeout', type=int, default=10, help='Timeout for API requests in seconds')
        parser.add_argument('--api-rate-limit', type=float, default=0.5, help='Seconds to wait between API calls')
        parser.add_argument('--max-runtime', type=int, default=0, help='Maximum runtime in minutes (0 for unlimited)')

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
    
    def fetch_station_info(self, station_id, timeout=10):
        """Fetch station information from external sources"""
        
        # Skip if we've previously failed for this ID during this run
        if hasattr(self, '_failed_lookups') and station_id in self._failed_lookups:
            return None
            
        # Ensure we have a place to track failed lookups
        if not hasattr(self, '_failed_lookups'):
            self._failed_lookups = set()
        
        # Set up rate limiting if needed
        if not hasattr(self, '_last_api_call'):
            self._last_api_call = None
            
        # Rate limiting
        if self._last_api_call is not None:
            elapsed = time.time() - self._last_api_call
            if elapsed < self._api_rate_limit:
                time.sleep(self._api_rate_limit - elapsed)
        
        # Try NOAA/NWS API for US stations (typically starting with K)
        if station_id.startswith('K') or station_id.startswith('P') or station_id.startswith('T'):
            try:
                # First try as a regular station
                url = f"https://api.weather.gov/stations/{station_id}"
                self._last_api_call = time.time()
                response = requests.get(url, timeout=timeout, headers={'User-Agent': 'EMWIN-Processor'})
                
                if response.status_code == 200:
                    data = response.json()
                    result = {
                        'name': data.get('name') or data.get('properties', {}).get('name'),
                        'location': f"{data.get('county', '')}, {data.get('state', '')}".strip(', '),
                        'latitude': data.get('geometry', {}).get('coordinates', [None, None])[1],
                        'longitude': data.get('geometry', {}).get('coordinates', [None, None])[0],
                        'elevation_meters': data.get('elevation', {}).get('value'),
                        'type': 'Weather Station',
                        'state': data.get('state') or data.get('properties', {}).get('state'),
                        'country': 'US'
                    }
                    return result
                elif response.status_code == 404 and len(station_id) == 4 and station_id[0] in "KPTNC":
                    # If it's a 4-character ID starting with a regional prefix, try as an office
                    office_id = station_id[1:]  # Remove the prefix
                    url = f"https://api.weather.gov/offices/{office_id}"
                    # Rate limiting
                    time.sleep(self._api_rate_limit)
                    self._last_api_call = time.time()
                    response = requests.get(url, timeout=timeout, headers={'User-Agent': 'EMWIN-Processor'})
                    
                    if response.status_code == 200:
                        data = response.json()
                        result = {
                            'name': data.get('properties', {}).get('name'),
                            'location': data.get('properties', {}).get('address', {}).get('addressLocality', ''),
                            'latitude': data.get('geometry', {}).get('coordinates', [None, None])[1],
                            'longitude': data.get('geometry', {}).get('coordinates', [None, None])[0],
                            'type': 'Weather Forecast Office',
                            'state': data.get('properties', {}).get('address', {}).get('addressRegion'),
                            'country': 'US'
                        }
                        return result
                
                # If both failed and it might be a radar station, try the radar endpoint
                if response.status_code == 404:
                    url = f"https://api.weather.gov/radar/stations/{station_id}"
                    # Rate limiting
                    time.sleep(self._api_rate_limit)
                    self._last_api_call = time.time()
                    response = requests.get(url, timeout=timeout, headers={'User-Agent': 'EMWIN-Processor'})
                    
                    if response.status_code == 200:
                        data = response.json()
                        result = {
                            'name': data.get('properties', {}).get('name'),
                            'location': f"Radar Station - {data.get('properties', {}).get('name', '')}",
                            'latitude': data.get('geometry', {}).get('coordinates', [None, None])[1],
                            'longitude': data.get('geometry', {}).get('coordinates', [None, None])[0],
                            'elevation_meters': data.get('properties', {}).get('elevation'),
                            'type': 'Weather Radar',
                            'state': None,  # Radar API doesn't provide state
                            'country': 'US'
                        }
                        return result
                
                # All attempts failed, cache this failed lookup
                if response.status_code == 404:
                    logger.debug(f"All Weather.gov APIs returned 404 for station {station_id}")
                    self._failed_lookups.add(station_id)
                    return None
                
            except Exception as e:
                logger.warning(f"Error fetching US station {station_id}: {str(e)}")

        # Try Environment Canada API for Canadian stations (starting with C)
        if station_id.startswith('C'):
            try:
                url = f"https://api.weather.gc.ca/collections/stations/items?STATION_ID={station_id}"
                response = requests.get(url, timeout=timeout)
                if response.status_code == 200:
                    data = response.json()
                    if data.get('features') and len(data['features']) > 0:
                        station = data['features'][0]['properties']
                        return {
                            'name': station.get('STATION_NAME'),
                            'location': f"{station.get('MUNICIPALITY')}, {station.get('PROVINCE')}",
                            'latitude': station.get('LATITUDE'),
                            'longitude': station.get('LONGITUDE'),
                            'elevation_meters': station.get('ELEVATION'),
                            'type': station.get('STATION_TYPE'),
                            'state': station.get('PROVINCE'),
                            'country': 'CA'
                        }
                elif response.status_code == 404:
                    # Don't log a warning for 404 responses
                    self._failed_lookups.add(station_id)
                    return None
                else:
                    logger.debug(f"Environment Canada API returned status {response.status_code} for station {station_id}")
            except Exception as e:
                logger.warning(f"Error fetching Canadian station {station_id}: {str(e)}")
        
        # Skip WMO API for stations with known patterns (to reduce unnecessary lookups)
        if station_id.startswith('K') or station_id.startswith('P') or station_id.startswith('N'):
            # These are likely US or international station patterns that the WMO API won't have
            self._failed_lookups.add(station_id)
            return None
                
        # Try WMO API only for station patterns that might be in their database
        try:
            url = f"https://api.wmo.int/v1/stations/{station_id}"
            # Use a shorter timeout for WMO API since it often doesn't resolve
            wmo_timeout = min(timeout, 5)
            response = requests.get(url, timeout=wmo_timeout)
            if response.status_code == 200:
                data = response.json()
                return {
                    'name': data.get('name'),
                    'location': data.get('location'),
                    'latitude': data.get('latitude'),
                    'longitude': data.get('longitude'),
                    'elevation_meters': data.get('elevation'),
                    'type': data.get('type'),
                    'state': data.get('region'),
                    'country': data.get('country')
                }
            elif response.status_code == 404:
                # Don't log a warning for 404 responses
                self._failed_lookups.add(station_id)
                return None
        except requests.exceptions.ConnectionError:
            # Silently cache connection failures to WMO API
            self._failed_lookups.add(station_id)
            return None
        except Exception as e:
            logger.debug(f"Error fetching WMO station {station_id}: {str(e)}")
            self._failed_lookups.add(station_id)
        
        # # Try OpenWeatherMap API as a fallback
        # try:
        #     api_key = getattr(settings, 'OPENWEATHERMAP_API_KEY', None)
        #     if api_key:
        #         url = f"https://api.openweathermap.org/data/2.5/weather?q={station_id}&appid={api_key}"
        #         response = requests.get(url, timeout=timeout)
        #         if response.status_code == 200:
        #             data = response.json()
        #             return {
        #                 'name': data.get('name'),
        #                 'location': f"{data.get('name')}, {data.get('sys', {}).get('country')}",
        #                 'latitude': data.get('coord', {}).get('lat'),
        #                 'longitude': data.get('coord', {}).get('lon'),
        #                 'elevation_meters': None,  # Not provided by this API
        #                 'type': 'Weather Station',
        #                 'state': None,  # Not provided by this API
        #                 'country': data.get('sys', {}).get('country')
        #             }
        # except Exception as e:
        #     logger.warning(f"Error fetching OpenWeatherMap data for {station_id}: {str(e)}")
        
        # Remember this failed lookup for future reference
        self._failed_lookups.add(station_id)
        return None
        
    def handle(self, *args, **options):
        directory = options['directory']
        batch_size = options['batch_size']
        preview_length = options['preview_length']
        clean = options['clean']
        clean_all = options['clean_all'] 
        clean_confirm = options['clean_confirm']
        lookup_stations = options['lookup_stations']
        lookup_missing_only = options['lookup_missing_only']
        lookup_timeout = options['lookup_timeout']
        self._api_rate_limit = options.get('api_rate_limit', 0.5)  # Default to 0.5s between API calls
        max_runtime = options.get('max_runtime', 0)  # In minutes
        
        # Convert max_runtime to seconds
        max_runtime_seconds = max_runtime * 60 if max_runtime > 0 else 0
        start_time = time.time()
        
        # Define max_failures variable for station lookup limits
        max_failures = 500  # Default to 100 failures before disabling lookups
        
        # Initialize tracking for failed lookups to avoid retrying within the same run
        self._failed_lookups = set()
        self._last_api_call = None
        
        # If we're only supposed to look up missing stations, we don't need to pre-load
        # anything - the database query in the loop will handle this
        
        # Handle clean operations if requested
        if clean or clean_all:
            if not clean_confirm:
                # Ask for confirmation if not already confirmed
                file_count = EMWINFile.objects.count()
                if clean_all:
                    product_count = EMWINProduct.objects.count()
                    station_count = EMWINStation.objects.count()
                    confirm_message = f"This will delete {file_count} EMWIN files, {product_count} products, and {station_count} stations. Are you sure? (y/N): "
                else:
                    confirm_message = f"This will delete {file_count} EMWIN files. Are you sure? (y/N): "
                
                confirm = input(confirm_message).lower() == 'y'
                if not confirm:
                    self.stdout.write(self.style.WARNING("Operation cancelled."))
                    return
            
            # Perform clean operation
            with transaction.atomic():
                if clean_all:
                    self.stdout.write("Deleting all EMWIN data...")
                    EMWINFile.objects.all().delete()
                    EMWINProduct.objects.all().delete()
                    EMWINStation.objects.all().delete()
                    self.stdout.write(self.style.SUCCESS("All EMWIN data deleted."))
                else:
                    self.stdout.write("Deleting EMWIN files...")
                    deleted_count = EMWINFile.objects.all().delete()[0]
                    self.stdout.write(self.style.SUCCESS(f"{deleted_count} EMWIN files deleted."))
                    
                    # Clean up unused products and stations - Use a different name for the annotation
                    unused_products = EMWINProduct.objects.annotate(
                        files_count=Count('emwinfiles')
                    ).filter(files_count=0)
                    
                    unused_stations = EMWINStation.objects.annotate(
                        files_count=Count('emwinfiles')
                    ).filter(files_count=0)
                    
                    product_count = unused_products.count()
                    station_count = unused_stations.count()
                    
                    if product_count > 0 or station_count > 0:
                        self.stdout.write("Cleaning up unused products and stations...")
                        unused_products.delete()
                        unused_stations.delete()
                        self.stdout.write(self.style.SUCCESS(f"Deleted {product_count} unused products and {station_count} unused stations."))
        
        # Now proceed with file processing
        self.stdout.write(f"Processing EMWIN files in {directory}")
        
        # Check if directory exists
        if not os.path.isdir(directory):
            raise CommandError(f"Directory {directory} does not exist")
        
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
            'SPCMESO': {'name': 'Mesoscale Discussion', 'category': 'Severe Weather', 'description': 'Storm Prediction Center mesoscale weather discussions'},
            'SPCSWOD': {'name': 'Day 1 Convective Outlook', 'category': 'Severe Weather', 'description': 'Storm Prediction Center Day 1 Convective Outlook'},
            'SPCSWOU': {'name': 'Day 2 Convective Outlook', 'category': 'Severe Weather', 'description': 'Storm Prediction Center Day 2 Convective Outlook'},
            'SPCSWO2': {'name': 'Day 3 Convective Outlook', 'category': 'Severe Weather', 'description': 'Storm Prediction Center Day 3 Convective Outlook'},
            'SPCSWOX': {'name': 'Day 4-8 Convective Outlook', 'category': 'Severe Weather', 'description': 'Storm Prediction Center Days 4-8 Convective Outlook'},
            'TCDAT1': {'name': 'Tropical Cyclone Discussion', 'category': 'Tropical Weather', 'description': 'Tropical cyclone discussion from NHC'},
            'TCPAT1': {'name': 'Tropical Cyclone Public Advisory', 'category': 'Tropical Weather', 'description': 'Tropical cyclone public advisory from NHC'},
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
            'KNHC': {
                'name': 'National Hurricane Center', 
                'location': 'Miami, FL',
                'latitude': 25.7617,
                'longitude': -80.1918,
                'elevation_meters': 2,
                'type': 'Weather Forecast Office',
                'state': 'FL',
                'country': 'US'
            },
            'KSPC': {
                'name': 'Storm Prediction Center', 
                'location': 'Norman, OK',
                'latitude': 35.1833,
                'longitude': -97.4167,
                'elevation_meters': 357,
                'type': 'Weather Forecast Office',
                'state': 'OK',
                'country': 'US'
            },
        }
        
        # Process files in batches
        files_to_create = []
        total_processed = 0
        total_new = 0
        skipped_files = 0
        error_files = 0
        
        # Get list of files to process
        try:
            file_list = [f for f in os.listdir(directory) if f.startswith("A_") and f.endswith(".TXT")]
            total_files = len(file_list)
            self.stdout.write(f"Found {total_files} EMWIN files in directory")
            
            # Add a progress reporting line
            self.stdout.write("Starting processing... (this may take some time)")
            start_time = time.time()
            last_update = start_time
        except Exception as e:
            raise CommandError(f"Error reading directory: {str(e)}")
        
        # Process each file
        for idx, filename in enumerate(file_list):
            # Add progress indicator every 5 seconds
            current_time = time.time()
            if current_time - last_update > 5:
                elapsed = current_time - start_time
                percent_done = (idx / total_files) * 100
                files_per_second = idx / elapsed if elapsed > 0 else 0
                est_remaining = (total_files - idx) / files_per_second if files_per_second > 0 else "unknown"
                
                if isinstance(est_remaining, float):
                    hours, remainder = divmod(est_remaining, 3600)
                    minutes, seconds = divmod(remainder, 60)
                    remaining_str = f"{int(hours)}h {int(minutes)}m {int(seconds)}s"
                else:
                    remaining_str = est_remaining
                    
                self.stdout.write(
                    f"Progress: {idx}/{total_files} ({percent_done:.1f}%) - "
                    f"Speed: {files_per_second:.1f} files/sec - "
                    f"Estimated remaining: {remaining_str}"
                )
                last_update = current_time

            # Skip if already in database
            if filename in existing_filenames:
                skipped_files += 1
                if skipped_files % 1000 == 0:
                    self.stdout.write(f"Skipped {skipped_files} existing files...")
                continue
                
            parsed = self.parse_emwin_filename(filename)
            if not parsed:
                error_files += 1
                continue
                
            file_path = os.path.join(directory, filename)
            
            try:
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
                    
                    # Try to fetch station information from external APIs if requested
                    if lookup_stations:
                        # For lookup_missing_only, we're creating a new station, so it's missing by definition
                        # No need to check if it has complete info
                        
                        # Skip lookups if we've hit too many failures
                        if len(self._failed_lookups) > max_failures:
                            if not hasattr(self, '_notified_lookup_disabled'):
                                self.stdout.write(self.style.WARNING(
                                    f"Disabled station lookups after {len(self._failed_lookups)} failures"
                                ))
                                self._notified_lookup_disabled = True
                        else:
                            station_info = self.fetch_station_info(station_id, timeout=lookup_timeout)
                            if station_info:
                                # Only update fields that are not already set
                                for key, value in station_info.items():
                                    if value is not None and (key not in defaults or defaults[key] is None or defaults[key] == ''):
                                        defaults[key] = value
                    
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
                if total_processed % 1000 == 0:
                    self.stdout.write(f"Processed {total_processed} files, added {total_new} new ones, skipped {skipped_files}, errors {error_files}")
            
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error processing file {filename}: {str(e)}"))






                EMWINFile.objects.bulk_create(files_to_create)            with transaction.atomic():        if files_to_create:        # Create any remaining files                        error_files += 1            self.stdout.write(f"Added final {len(files_to_create)} files to database")
            
        self.stdout.write(self.style.SUCCESS(
            f"Successfully processed {total_processed} files. "
            f"Added {total_new} new files to database. "
            f"Skipped {skipped_files} existing files. "
            f"Encountered {error_files} errors."
        ))
        
        # Print summary of data in database
        file_count = EMWINFile.objects.count()
        product_count = EMWINProduct.objects.count()
        station_count = EMWINStation.objects.count()
        self.stdout.write(self.style.SUCCESS(
            f"Database now contains {file_count} files, {product_count} products, and {station_count} stations."
        ))
