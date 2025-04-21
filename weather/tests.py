from django.test import TestCase, Client
from django.urls import reverse
import json
from django.utils import timezone
import pytz
from datetime import datetime
from .models import OutdoorWeatherReading, IndoorSensor

class WeatherDataTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse('weather:receive_weather_data')
        
    def test_receive_outdoor_weather_data(self):
        """Test that outdoor weather data is properly received and stored with correct timezone"""
        # Sample data from a weather station
        data = {
            "time": "2025-04-21 13:34:47",
            "model": "Fineoffset-WH24",
            "id": 182,
            "battery_ok": 1,
            "temperature_C": 5.500,
            "humidity": 63,
            "wind_dir_deg": 38,
            "wind_avg_m_s": 0.000,
            "wind_max_m_s": 0.000,
            "rain_mm": 1461.300,
            "uv": 83,
            "uvi": 0,
            "light_lux": 10602.000,
            "mic": "CRC"
        }
        
        # Send the data to our endpoint
        response = self.client.post(
            self.url,
            data=json.dumps(data),
            content_type='application/json'
        )
        
        # Check that the request was successful
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'status': 'success'})
        
        # Check that a record was created in the database
        self.assertEqual(OutdoorWeatherReading.objects.count(), 1)
        
        # Get the created record
        reading = OutdoorWeatherReading.objects.first()
        
        # Check that timezone information was properly handled
        mountain_tz = pytz.timezone('America/Denver')
        naive_time = datetime.strptime("2025-04-21 13:34:47", '%Y-%m-%d %H:%M:%S')
        expected_time = mountain_tz.localize(naive_time)
        
        # Convert both to UTC for comparison if your Django settings use UTC
        if timezone.get_current_timezone().zone != 'America/Denver':
            expected_time = expected_time.astimezone(timezone.utc)
            reading_time = reading.time.astimezone(timezone.utc)
        else:
            reading_time = reading.time
            
        self.assertEqual(reading_time, expected_time)
        
        # Check that other fields were stored correctly
        self.assertEqual(reading.model, "Fineoffset-WH24")
        self.assertEqual(reading.sensor_id, 182)
        self.assertEqual(reading.temperature_C, 5.5)
        self.assertEqual(reading.humidity, 63)
        self.assertEqual(reading.rain_mm, 1461.3)
        
        # Test the conversion properties
        self.assertEqual(reading.temperature_F, 41.9)
        self.assertEqual(reading.rain_inches, 57.53)
        
    def test_receive_indoor_sensor_data(self):
        """Test that indoor sensor data is properly received and stored"""
        data = {
            "time": "2025-04-21 14:03:12",
            "model": "Fineoffset-WN32P",
            "id": 105,
            "battery_ok": 1,
            "temperature_C": 21.800,
            "humidity": 42,
            "mic": "CRC"
        }
        
        # Send the data to our endpoint
        response = self.client.post(
            self.url,
            data=json.dumps(data),
            content_type='application/json'
        )
        
        # Check that the request was successful
        self.assertEqual(response.status_code, 200)
        
        # Check that a record was created in the database
        self.assertEqual(IndoorSensor.objects.count(), 1)
        
        # Get the created record
        reading = IndoorSensor.objects.first()
        
        # Check that fields were stored correctly
        self.assertEqual(reading.model, "Fineoffset-WN32P")
        self.assertEqual(reading.sensor_id, 105)
        self.assertEqual(reading.temperature_C, 21.8)
        self.assertEqual(reading.temperature_F, 71.2)  # Test conversion property
