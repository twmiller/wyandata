from datetime import timedelta, date
from django.db import transaction
from django.db.models import Avg, Max, Min, Sum, Count
from django.utils import timezone
from .models import SolarControllerData, SolarDailyAggregate, SolarMonthlyAggregate, SolarYearlyAggregate, SolarTotalAggregate

def cleanup_old_solar_data(days=7):
    """
    Clean up solar controller data older than the specified number of days.
    This should be run as a scheduled task AFTER aggregation.
    """
    # Before cleaning up, make sure aggregation has been done for any old data
    cutoff_date = timezone.now().date() - timedelta(days=days)
    
    # Run aggregation for any days in the cleanup period that don't have aggregates yet
    # This ensures we don't lose data before it's aggregated
    for day_offset in range(days, 0, -1):
        target_date = timezone.now().date() - timedelta(days=day_offset)
        # Only aggregate if we don't already have an aggregate for this day
        if not SolarDailyAggregate.objects.filter(date=target_date).exists():
            calculate_daily_aggregate(target_date)
    
    # Update monthly aggregates for any months in the cleanup period that don't have aggregates yet
    months_to_check = set()
    for day_offset in range(days, 0, -1):
        target_date = timezone.now().date() - timedelta(days=day_offset)
        months_to_check.add((target_date.year, target_date.month))
    
    for year, month in months_to_check:
        # Only aggregate if we don't already have an aggregate for this month
        if not SolarMonthlyAggregate.objects.filter(year=year, month=month).exists():
            calculate_monthly_aggregate(year, month)
    
    # Update yearly aggregates for any years in the cleanup period that don't have aggregates yet
    years_to_check = set(year for year, _ in months_to_check)
    for year in years_to_check:
        # Only aggregate if we don't already have an aggregate for this year
        if not SolarYearlyAggregate.objects.filter(year=year).exists():
            calculate_yearly_aggregate(year)
    
    # Always update the total aggregate
    update_total_aggregate()
    
    # Now that we've ensured all aggregates are up-to-date, clean up old raw data
    cutoff_datetime = timezone.now() - timedelta(days=days)
    with transaction.atomic():
        old_records = SolarControllerData.objects.filter(timestamp__lt=cutoff_datetime)
        count = old_records.count()
        old_records.delete()
        
    return count

def calculate_daily_aggregate(target_date=None):
    """
    Calculate daily aggregated metrics for the specified date.
    If no date is provided, yesterday's data will be aggregated.
    
    Note: This assumes data points are collected at regular intervals.
    """
    if target_date is None:
        # Default to yesterday
        target_date = timezone.now().date() - timedelta(days=1)
    
    # Check if we already have an aggregate for this day to avoid double-counting
    existing_aggregate = SolarDailyAggregate.objects.filter(date=target_date).first()
    if existing_aggregate:
        # We already have an aggregate for this day
        return existing_aggregate
    
    # Get all data points for the target date
    start_datetime = timezone.make_aware(timezone.datetime.combine(target_date, timezone.datetime.min.time()))
    end_datetime = timezone.make_aware(timezone.datetime.combine(target_date, timezone.datetime.max.time()))
    
    data_points = SolarControllerData.objects.filter(
        timestamp__gte=start_datetime,
        timestamp__lte=end_datetime
    )
    
    if not data_points.exists():
        return None  # No data for this day
    
    # Calculate aggregates
    with transaction.atomic():
        # Create a new daily aggregate record
        daily_agg = SolarDailyAggregate(date=target_date)
        
        # Calculate battery stats
        battery_stats = data_points.aggregate(
            min_voltage=Min('battery_voltage'),
            max_voltage=Max('battery_voltage'),
            avg_voltage=Avg('battery_voltage')
        )
        
        daily_agg.min_battery_voltage = battery_stats['min_voltage']
        daily_agg.max_battery_voltage = battery_stats['max_voltage']
        daily_agg.avg_battery_voltage = battery_stats['avg_voltage']
        
        # Find peak power values
        daily_agg.peak_power = data_points.aggregate(max_power=Max('pv_array_power'))['max_power'] or 0
        daily_agg.peak_load = data_points.aggregate(max_load=Max('load_power'))['max_load'] or 0
        
        # Calculate energy production (Wh)
        # For accurate energy calculation, we need regular intervals
        # Simplified approach: average power × time period
        if data_points.count() > 1:
            avg_power = data_points.aggregate(avg=Avg('pv_array_power'))['avg'] or 0
            avg_load = data_points.aggregate(avg=Avg('load_power'))['avg'] or 0
            
            # Assuming we have regular readings over 24 hours
            # Energy = average power (W) × time (h)
            daily_agg.energy_produced = avg_power * 24  # Wh
            daily_agg.energy_consumed = avg_load * 24   # Wh
            
            # Count sunshine hours (periods with substantial generation)
            # Define "substantial" as >5% of peak power
            sunshine_threshold = max(50, daily_agg.peak_power * 0.05)  # At least 50W or 5% of peak
            sunshine_points = data_points.filter(pv_array_power__gt=sunshine_threshold).count()
            
            # Calculate sunshine hours based on proportion of data points
            if sunshine_points > 0:
                daily_agg.sunshine_hours = (sunshine_points / data_points.count()) * 24
        
        daily_agg.save()
        return daily_agg

def calculate_monthly_aggregate(year=None, month=None):
    """Calculate monthly aggregated metrics."""
    if year is None or month is None:
        # Default to last month
        today = timezone.now().date()
        first_of_month = date(today.year, today.month, 1)
        last_month = first_of_month - timedelta(days=1)
        year = last_month.year
        month = last_month.month
    
    # Check if we already have an aggregate for this month to avoid double-counting
    existing_aggregate = SolarMonthlyAggregate.objects.filter(year=year, month=month).first()
    if existing_aggregate:
        # We already have an aggregate for this month
        return existing_aggregate
    
    # Get all daily aggregates for the month
    daily_aggs = SolarDailyAggregate.objects.filter(date__year=year, date__month=month)
    
    if not daily_aggs.exists():
        return None  # No data for this month
    
    with transaction.atomic():
        # Get or create the monthly aggregate record
        monthly_agg, created = SolarMonthlyAggregate.objects.get_or_create(year=year, month=month)
        
        # Sum up daily production
        total_energy = daily_aggs.aggregate(sum=Sum('energy_produced'))['sum'] or 0
        monthly_agg.energy_produced = total_energy / 1000  # Convert Wh to kWh
        
        total_consumption = daily_aggs.aggregate(sum=Sum('energy_consumed'))['sum'] or 0
        monthly_agg.energy_consumed = total_consumption / 1000  # Convert Wh to kWh
        
        # Peak power for the month
        monthly_agg.peak_power = daily_aggs.aggregate(max=Max('peak_power'))['max'] or 0
        
        # Count days with production
        production_days = daily_aggs.filter(energy_produced__gt=0).count()
        monthly_agg.production_days = production_days
        
        if production_days > 0:
            monthly_agg.avg_daily_production = monthly_agg.energy_produced / production_days
        
        # Find best day
        best_day = daily_aggs.order_by('-energy_produced').first()
        if best_day:
            monthly_agg.best_day = best_day.date
            monthly_agg.best_day_production = best_day.energy_produced / 1000  # Convert to kWh
        
        monthly_agg.save()
        return monthly_agg

def calculate_yearly_aggregate(year=None):
    """Calculate yearly aggregated metrics."""
    if year is None:
        # Default to last year
        year = timezone.now().year - 1
    
    # Check if we already have an aggregate for this year to avoid double-counting
    existing_aggregate = SolarYearlyAggregate.objects.filter(year=year).first()
    if existing_aggregate:
        # We already have an aggregate for this year
        return existing_aggregate
    
    # Get all monthly aggregates for the year
    monthly_aggs = SolarMonthlyAggregate.objects.filter(year=year)
    
    if not monthly_aggs.exists():
        return None  # No data for this year
    
    with transaction.atomic():
        # Get or create the yearly aggregate record
        yearly_agg, created = SolarYearlyAggregate.objects.get_or_create(year=year)
        
        # Sum up monthly production
        yearly_agg.energy_produced = monthly_aggs.aggregate(sum=Sum('energy_produced'))['sum'] or 0
        yearly_agg.energy_consumed = monthly_aggs.aggregate(sum=Sum('energy_consumed'))['sum'] or 0
        
        # Peak power for the year
        yearly_agg.peak_power = monthly_aggs.aggregate(max=Max('peak_power'))['max'] or 0
        
        # Calculate average monthly production
        active_months = monthly_aggs.count()
        if active_months > 0:
            yearly_agg.avg_monthly_production = yearly_agg.energy_produced / active_months
        
        # Find best month
        best_month = monthly_aggs.order_by('-energy_produced').first()
        if best_month:
            yearly_agg.best_month = best_month.month
            yearly_agg.best_month_production = best_month.energy_produced
        
        yearly_agg.save()
        return yearly_agg

def update_total_aggregate():
    """Update the total lifetime aggregate statistics."""
    # For total aggregate, we always update the single record
    # No risk of double-counting as we're summing from the already-aggregated
    # yearly data, which is guaranteed to be non-overlapping
    
    # Get all yearly aggregates
    yearly_aggs = SolarYearlyAggregate.objects.all()
    
    # Get all daily aggregates for finding absolute peaks
    daily_aggs = SolarDailyAggregate.objects.all()
    
    with transaction.atomic():
        # Get or create the total aggregate record (there should only be one)
        total_agg, created = SolarTotalAggregate.objects.get_or_create(id=1)
        
        # Sum up yearly production
        total_agg.total_energy_produced = yearly_aggs.aggregate(sum=Sum('energy_produced'))['sum'] or 0
        total_agg.total_energy_consumed = yearly_aggs.aggregate(sum=Sum('energy_consumed'))['sum'] or 0
        
        # Find all-time peak power
        peak_power_day = daily_aggs.order_by('-peak_power').first()
        if peak_power_day:
            total_agg.peak_power_ever = peak_power_day.peak_power
            total_agg.peak_power_date = peak_power_day.date
        
        # Find best day ever
        best_day = daily_aggs.order_by('-energy_produced').first()
        if best_day:
            total_agg.best_day_ever = best_day.date
            total_agg.best_day_production = best_day.energy_produced / 1000  # Convert to kWh
        
        # Find best month ever
        best_month = SolarMonthlyAggregate.objects.order_by('-energy_produced').first()
        if best_month:
            total_agg.best_month_ever = f"{best_month.year}-{best_month.month:02d}"
            total_agg.best_month_production = best_month.energy_produced
        
        # Calculate operational days
        if daily_aggs.exists():
            first_day = daily_aggs.order_by('date').first().date
            last_day = daily_aggs.order_by('-date').first().date
            
            # Set install date if not already set
            if not total_agg.system_install_date:
                total_agg.system_install_date = first_day
                
            # Calculate days between first and last record
            total_agg.operational_days = (last_day - first_day).days + 1
        
        total_agg.save()
        return total_agg

def run_daily_aggregation():
    """Run the daily aggregation process, typically scheduled to run after midnight."""
    yesterday = timezone.now().date() - timedelta(days=1)
    
    # Step 1: Check if yesterday's data has already been aggregated to avoid double-counting
    if not SolarDailyAggregate.objects.filter(date=yesterday).exists():
        # Only aggregate if we haven't already
        daily_agg = calculate_daily_aggregate(yesterday)
    
    # Step 2: If it's the first day of the month, check if previous month needs aggregation
    today = timezone.now().date()
    if today.day == 1:
        first_of_month = date(today.year, today.month, 1)
        last_month = first_of_month - timedelta(days=1)
        
        # Only aggregate if we haven't already
        if not SolarMonthlyAggregate.objects.filter(year=last_month.year, month=last_month.month).exists():
            monthly_agg = calculate_monthly_aggregate(last_month.year, last_month.month)
        
        # Step 3: If it's also January 1st, check if previous year needs aggregation
        if today.month == 1:
            # Only aggregate if we haven't already
            if not SolarYearlyAggregate.objects.filter(year=today.year - 1).exists():
                yearly_agg = calculate_yearly_aggregate(today.year - 1)
    
    # Step 4: Always update the total aggregate (this won't double-count as it sums from yearly data)
    update_total_aggregate()
