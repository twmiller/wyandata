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
