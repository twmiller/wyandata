from django.db import models

class SolarControllerData(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True)
    
    # Controller info
    array_rated_voltage = models.FloatField(null=True, blank=True)
    array_rated_current = models.FloatField(null=True, blank=True)
    array_rated_power = models.FloatField(null=True, blank=True)
    battery_rated_voltage = models.FloatField(null=True, blank=True)
    battery_rated_current = models.FloatField(null=True, blank=True)
    battery_rated_power = models.FloatField(null=True, blank=True)
    charging_mode = models.CharField(max_length=20, null=True, blank=True)
    rated_load_current = models.FloatField(null=True, blank=True)
    
    # Real-time data
    pv_array_voltage = models.FloatField(null=True, blank=True)
    pv_array_current = models.FloatField(null=True, blank=True)
    pv_array_power = models.FloatField(null=True, blank=True)
    battery_voltage = models.FloatField(null=True, blank=True)
    battery_charging_current = models.FloatField(null=True, blank=True)
    battery_charging_power = models.FloatField(null=True, blank=True)
    load_voltage = models.FloatField(null=True, blank=True)
    load_current = models.FloatField(null=True, blank=True)
    load_power = models.FloatField(null=True, blank=True)
    battery_temp = models.FloatField(null=True, blank=True)
    controller_temp = models.FloatField(null=True, blank=True)
    heat_sink_temp = models.FloatField(null=True, blank=True)
    
    # Controller settings
    battery_type = models.CharField(max_length=50, null=True, blank=True)
    battery_capacity = models.IntegerField(null=True, blank=True)
    high_voltage_disconnect = models.FloatField(null=True, blank=True)
    charging_limit_voltage = models.FloatField(null=True, blank=True)
    equalization_voltage = models.FloatField(null=True, blank=True)
    boost_voltage = models.FloatField(null=True, blank=True)
    float_voltage = models.FloatField(null=True, blank=True)
    low_voltage_reconnect = models.FloatField(null=True, blank=True)
    low_voltage_disconnect = models.FloatField(null=True, blank=True)
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Solar Controller Data'
        verbose_name_plural = 'Solar Controller Data'
        
    def __str__(self):
        return f"Solar data from {self.timestamp}"

class SolarDailyAggregate(models.Model):
    """Daily aggregated solar data"""
    date = models.DateField(unique=True)
    
    # Energy produced
    energy_produced = models.FloatField(default=0.0, help_text="Daily energy produced in Wh")
    peak_power = models.FloatField(default=0.0, help_text="Peak power during the day in W")
    
    # Battery stats
    min_battery_voltage = models.FloatField(null=True, help_text="Minimum battery voltage")
    max_battery_voltage = models.FloatField(null=True, help_text="Maximum battery voltage")
    avg_battery_voltage = models.FloatField(null=True, help_text="Average battery voltage")
    
    # Load stats
    energy_consumed = models.FloatField(default=0.0, help_text="Daily energy consumed in Wh")
    peak_load = models.FloatField(default=0.0, help_text="Peak load during the day in W")
    
    # Weather influence
    sunshine_hours = models.FloatField(null=True, blank=True, help_text="Hours with significant solar production")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-date']
        verbose_name = "Solar Daily Aggregate"
        verbose_name_plural = "Solar Daily Aggregates"
        
    def __str__(self):
        return f"Solar data for {self.date}"

class SolarMonthlyAggregate(models.Model):
    """Monthly aggregated solar data"""
    year = models.IntegerField()
    month = models.IntegerField()  # 1-12
    
    # Energy statistics
    energy_produced = models.FloatField(default=0.0, help_text="Monthly energy produced in kWh")
    energy_consumed = models.FloatField(default=0.0, help_text="Monthly energy consumed in kWh")
    peak_power = models.FloatField(default=0.0, help_text="Peak power during the month in W")
    
    # Performance metrics
    avg_daily_production = models.FloatField(default=0.0, help_text="Average daily production in kWh")
    production_days = models.IntegerField(default=0, help_text="Number of days with production")
    best_day = models.DateField(null=True, blank=True, help_text="Day with highest production")
    best_day_production = models.FloatField(default=0.0, help_text="Highest daily production in kWh")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-year', '-month']
        unique_together = ('year', 'month')
        verbose_name = "Solar Monthly Aggregate"
        verbose_name_plural = "Solar Monthly Aggregates"
        
    def __str__(self):
        return f"Solar data for {self.year}-{self.month:02d}"

class SolarYearlyAggregate(models.Model):
    """Yearly aggregated solar data"""
    year = models.IntegerField(unique=True)
    
    # Energy statistics
    energy_produced = models.FloatField(default=0.0, help_text="Yearly energy produced in kWh")
    energy_consumed = models.FloatField(default=0.0, help_text="Yearly energy consumed in kWh")
    peak_power = models.FloatField(default=0.0, help_text="Peak power during the year in W")
    
    # Performance metrics
    best_month = models.IntegerField(null=True, blank=True, help_text="Month with highest production (1-12)")
    best_month_production = models.FloatField(default=0.0, help_text="Highest monthly production in kWh")
    avg_monthly_production = models.FloatField(default=0.0, help_text="Average monthly production in kWh")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-year']
        verbose_name = "Solar Yearly Aggregate"
        verbose_name_plural = "Solar Yearly Aggregates"
        
    def __str__(self):
        return f"Solar data for {self.year}"

class SolarTotalAggregate(models.Model):
    """Total lifetime aggregated solar data"""
    # There will only be one record in this table
    
    # Energy statistics
    total_energy_produced = models.FloatField(default=0.0, help_text="Total lifetime energy produced in kWh")
    total_energy_consumed = models.FloatField(default=0.0, help_text="Total lifetime energy consumed in kWh")
    peak_power_ever = models.FloatField(default=0.0, help_text="Highest power ever recorded in W")
    peak_power_date = models.DateField(null=True, blank=True, help_text="Date of highest power")
    
    # System information
    system_install_date = models.DateField(null=True, blank=True)
    panel_capacity = models.FloatField(null=True, blank=True, help_text="Total panel capacity in W")
    
    # Performance metrics
    best_day_ever = models.DateField(null=True, blank=True)
    best_day_production = models.FloatField(default=0.0, help_text="Best daily production in kWh")
    best_month_ever = models.CharField(max_length=7, null=True, blank=True, help_text="Format: YYYY-MM")
    best_month_production = models.FloatField(default=0.0, help_text="Best monthly production in kWh")
    
    operational_days = models.IntegerField(default=0, help_text="Number of days the system has been operational")
    
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Solar Total Aggregate"
        verbose_name_plural = "Solar Total Aggregates"
        
    def __str__(self):
        return "Solar Lifetime Statistics"
