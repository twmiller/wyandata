from django.core.management.base import BaseCommand
from django.db.models import Min, Max, Avg, Sum, Count
from django.utils import timezone
from weather.models import OutdoorWeatherReading, DailyWeatherSummary, MonthlyWeatherSummary
from datetime import datetime, timedelta, date
from collections import Counter
import pytz

class Command(BaseCommand):
    help = 'Generate daily and monthly weather summaries from raw readings'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='Number of days to look back and process (default: 7)'
        )
        parser.add_argument(
            '--regenerate',
            action='store_true',
            help='Force regeneration of existing summaries'
        )

    def handle(self, *args, **options):
        days_to_process = options['days']
        force_regenerate = options['regenerate']
        self.stdout.write(f'Processing summaries for the last {days_to_process} days...')
        
        # Get timezone-aware date range
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days_to_process-1)
        
        # Process daily summaries
        self._generate_daily_summaries(start_date, end_date, force_regenerate)
        
        # Process monthly summaries
        months_to_process = set()
        current_date = start_date
        while current_date <= end_date:
            months_to_process.add(current_date.strftime('%Y-%m'))
            current_date += timedelta(days=1)
            
        for year_month in months_to_process:
            self._generate_monthly_summary(year_month, force_regenerate)
            
        self.stdout.write(self.style.SUCCESS(f'Successfully processed weather summaries'))

    def _generate_daily_summaries(self, start_date, end_date, force_regenerate=False):
        """Generate summary for each day in the date range"""
        current_date = start_date
        while current_date <= end_date:
            # Check if summary already exists and we're not forcing regeneration
            if not force_regenerate and DailyWeatherSummary.objects.filter(date=current_date).exists():
                self.stdout.write(f'Skipping {current_date}, summary already exists')
                current_date += timedelta(days=1)
                continue
                
            # Get readings for the day
            day_start = datetime.combine(current_date, datetime.min.time())
            day_end = datetime.combine(current_date, datetime.max.time())
            
            # Make timezone-aware
            mountain_tz = pytz.timezone('America/Denver')
            day_start = mountain_tz.localize(day_start)
            day_end = mountain_tz.localize(day_end)
            
            # Get all readings for this day
            readings = OutdoorWeatherReading.objects.filter(
                time__range=(day_start, day_end)
            )
            
            if readings.exists():
                # Calculate aggregates
                temp_agg = readings.aggregate(
                    min_temp=Min('temperature_C'),
                    max_temp=Max('temperature_C'),
                    avg_temp=Avg('temperature_C')
                )
                
                humid_agg = readings.aggregate(
                    min_humidity=Min('humidity'),
                    max_humidity=Max('humidity'),
                    avg_humidity=Avg('humidity')
                )
                
                # Get predominant wind direction
                wind_directions = readings.exclude(wind_dir_deg__isnull=True).values_list('wind_direction_cardinal', flat=True)
                predominant_dir = None
                if wind_directions:
                    direction_counts = Counter(wind_directions)
                    predominant_dir = direction_counts.most_common(1)[0][0]
                
                # Calculate rainfall for the day
                first_reading = readings.filter(rain_mm__isnull=False).order_by('time').first()
                last_reading = readings.filter(rain_mm__isnull=False).order_by('-time').first()
                
                total_rainfall_mm = None
                if first_reading and last_reading and first_reading.rain_mm is not None and last_reading.rain_mm is not None:
                    # Calculate the difference between first and last reading of the day
                    total_rainfall_mm = max(0, last_reading.rain_mm - first_reading.rain_mm)
                
                # Create or update daily summary
                daily_summary, created = DailyWeatherSummary.objects.update_or_create(
                    date=current_date,
                    defaults={
                        'min_temp_c': temp_agg['min_temp'],
                        'max_temp_c': temp_agg['max_temp'],
                        'avg_temp_c': temp_agg['avg_temp'],
                        'min_humidity': humid_agg['min_humidity'],
                        'max_humidity': humid_agg['max_humidity'],
                        'avg_humidity': round(humid_agg['avg_humidity']) if humid_agg['avg_humidity'] is not None else None,
                        'total_rainfall_mm': total_rainfall_mm,
                        'max_wind_speed_mph': readings.aggregate(Max('wind_max_m_s'))['wind_max_m_s__max'] * 2.237 if readings.aggregate(Max('wind_max_m_s'))['wind_max_m_s__max'] is not None else None,
                        'predominant_wind_direction': predominant_dir,
                        'max_uvi': readings.aggregate(Max('uvi'))['uvi__max'],
                    }
                )
                
                self.stdout.write(f'{"Created" if created else "Updated"} summary for {current_date}')
            else:
                self.stdout.write(self.style.WARNING(f'No readings found for {current_date}, skipping'))
                
            current_date += timedelta(days=1)

    def _generate_monthly_summary(self, year_month, force_regenerate=False):
        """Generate summary for a specific year-month"""
        # Check if summary already exists and we're not forcing regeneration
        if not force_regenerate and MonthlyWeatherSummary.objects.filter(year_month=year_month).exists():
            self.stdout.write(f'Skipping {year_month}, summary already exists')
            return
            
        # Extract year and month
        year, month = map(int, year_month.split('-'))
        
        # Get all daily summaries for this month
        daily_summaries = DailyWeatherSummary.objects.filter(
            date__year=year,
            date__month=month
        )
        
        if daily_summaries.exists():
            # Calculate aggregates
            temp_agg = daily_summaries.aggregate(
                min_temp=Min('min_temp_c'),
                max_temp=Max('max_temp_c'),
                avg_temp=Avg('avg_temp_c')
            )
            
            # Calculate rainy days
            rainy_days = daily_summaries.filter(total_rainfall_mm__gt=0).count()
            
            # Calculate total rainfall
            total_rainfall = daily_summaries.aggregate(Sum('total_rainfall_mm'))['total_rainfall_mm__sum']
            
            # Get max wind speed
            max_wind = daily_summaries.aggregate(Max('max_wind_speed_mph'))['max_wind_speed_mph__max']
            
            # Create or update monthly summary
            monthly_summary, created = MonthlyWeatherSummary.objects.update_or_create(
                year_month=year_month,
                defaults={
                    'min_temp_c': temp_agg['min_temp'],
                    'max_temp_c': temp_agg['max_temp'],
                    'avg_temp_c': temp_agg['avg_temp'],
                    'total_rainfall_mm': total_rainfall,
                    'rainy_days': rainy_days,
                    'max_wind_speed_mph': max_wind
                }
            )
            
            self.stdout.write(f'{"Created" if created else "Updated"} summary for {year_month}')
        else:
            self.stdout.write(self.style.WARNING(f'No daily summaries found for {year_month}, skipping'))
