from django.db import models
import math

class BaseWeatherReading(models.Model):
    """Base model for all weather readings"""
    time = models.DateTimeField()
    model = models.CharField(max_length=50)
    sensor_id = models.IntegerField()
    battery_ok = models.BooleanField(default=True)
    temperature_C = models.FloatField(null=True, blank=True)
    humidity = models.IntegerField(null=True, blank=True)
    mic = models.CharField(max_length=10, null=True, blank=True)
    
    @property
    def temperature_F(self):
        """Convert Celsius to Fahrenheit"""
        if self.temperature_C is not None:
            return round((self.temperature_C * 9/5) + 32, 1)
        return None

    class Meta:
        abstract = True
        ordering = ['-time']

class OutdoorWeatherReading(BaseWeatherReading):
    """Model for outdoor weather stations (WH24 and WH65)"""
    wind_dir_deg = models.FloatField(null=True, blank=True)
    wind_avg_m_s = models.FloatField(null=True, blank=True)
    wind_max_m_s = models.FloatField(null=True, blank=True)
    rain_mm = models.FloatField(null=True, blank=True)
    uv = models.IntegerField(null=True, blank=True)
    uvi = models.IntegerField(null=True, blank=True)
    light_lux = models.FloatField(null=True, blank=True)
    
    @property
    def wind_avg_mph(self):
        """Convert m/s to mph"""
        if self.wind_avg_m_s is not None:
            return round(self.wind_avg_m_s * 2.237, 1)
        return None
    
    @property
    def wind_max_mph(self):
        """Convert m/s to mph"""
        if self.wind_max_m_s is not None:
            return round(self.wind_max_m_s * 2.237, 1)
        return None
    
    @property
    def rain_inches(self):
        """Convert mm to inches"""
        if self.rain_mm is not None:
            return round(self.rain_mm / 25.4, 2)
        return None
    
    @property
    def rainfall_since_previous(self):
        """Calculate rainfall since the previous reading"""
        if self.rain_mm is None:
            return None
            
        # Find the previous reading from the same sensor
        previous = OutdoorWeatherReading.objects.filter(
            sensor_id=self.sensor_id,
            model=self.model,
            time__lt=self.time,
            rain_mm__isnull=False
        ).order_by('-time').first()
        
        if previous and previous.rain_mm is not None:
            # Calculate difference in mm and convert to inches
            diff_mm = max(0, self.rain_mm - previous.rain_mm)  # Ensure non-negative
            return round(diff_mm / 25.4, 2)
        
        return None
    
    @property
    def wind_direction_cardinal(self):
        """Convert degrees to cardinal direction"""
        if self.wind_dir_deg is None:
            return None
            
        directions = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE',
                      'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW']
        idx = round(self.wind_dir_deg / 22.5) % 16
        return directions[idx]

class IndoorSensor(BaseWeatherReading):
    """Model for indoor sensors (WN32P and WH32B)"""
    channel = models.IntegerField(null=True, blank=True)
    pressure_hPa = models.FloatField(null=True, blank=True)
    
    @property
    def pressure_inHg(self):
        """Convert hectopascals to inches of mercury"""
        if self.pressure_hPa is not None:
            return round(self.pressure_hPa / 33.864, 2)
        return None
    
    class Meta:
        ordering = ['-time']

class DailyWeatherSummary(models.Model):
    """Daily weather statistics summary"""
    date = models.DateField(primary_key=True)
    min_temp_c = models.FloatField(null=True, blank=True)
    max_temp_c = models.FloatField(null=True, blank=True)
    avg_temp_c = models.FloatField(null=True, blank=True)
    min_humidity = models.IntegerField(null=True, blank=True)
    max_humidity = models.IntegerField(null=True, blank=True)
    avg_humidity = models.IntegerField(null=True, blank=True)
    total_rainfall_mm = models.FloatField(null=True, blank=True)
    max_wind_speed_mph = models.FloatField(null=True, blank=True)
    predominant_wind_direction = models.CharField(max_length=3, null=True, blank=True)
    max_uvi = models.IntegerField(null=True, blank=True)
    
    @property
    def min_temp_f(self):
        if self.min_temp_c is not None:
            return round((self.min_temp_c * 9/5) + 32, 1)
        return None
    
    @property
    def max_temp_f(self):
        if self.max_temp_c is not None:
            return round((self.max_temp_c * 9/5) + 32, 1)
        return None
    
    @property
    def avg_temp_f(self):
        if self.avg_temp_c is not None:
            return round((self.avg_temp_c * 9/5) + 32, 1)
        return None
    
    @property
    def total_rainfall_inches(self):
        if self.total_rainfall_mm is not None:
            return round(self.total_rainfall_mm / 25.4, 2)
        return None
    
    class Meta:
        ordering = ['-date']
        verbose_name_plural = "Daily weather summaries"

class MonthlyWeatherSummary(models.Model):
    """Monthly weather statistics summary"""
    year_month = models.CharField(max_length=7, primary_key=True)  # Format: YYYY-MM
    min_temp_c = models.FloatField(null=True, blank=True)
    max_temp_c = models.FloatField(null=True, blank=True)
    avg_temp_c = models.FloatField(null=True, blank=True)
    total_rainfall_mm = models.FloatField(null=True, blank=True)
    rainy_days = models.IntegerField(null=True, blank=True)
    max_wind_speed_mph = models.FloatField(null=True, blank=True)
    
    @property
    def min_temp_f(self):
        if self.min_temp_c is not None:
            return round((self.min_temp_c * 9/5) + 32, 1)
        return None
    
    @property
    def max_temp_f(self):
        if self.max_temp_c is not None:
            return round((self.max_temp_c * 9/5) + 32, 1)
        return None
    
    @property
    def avg_temp_f(self):
        if self.avg_temp_c is not None:
            return round((self.avg_temp_c * 9/5) + 32, 1)
        return None
    
    @property
    def total_rainfall_inches(self):
        if self.total_rainfall_mm is not None:
            return round(self.total_rainfall_mm / 25.4, 2)
        return None
    
    class Meta:
        ordering = ['-year_month']
        verbose_name_plural = "Monthly weather summaries"
