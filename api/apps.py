from django.apps import AppConfig

class ApiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'api'
    
    def ready(self):
        # Import the MQTT client module
        from wyandata import mqtt_client
        
        # Start the MQTT client
        mqtt_client.mqtt_client = mqtt_client.start_mqtt_client()