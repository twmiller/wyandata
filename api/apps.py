# api/apps.py
from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)

class ApiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'api'
    
    def ready(self):
        # Import the MQTT client module
        from wyandata import mqtt_client
        
        # Start the MQTT client only when not running management commands like migrate
        import sys
        if not ('makemigrations' in sys.argv or 'migrate' in sys.argv or 'collectstatic' in sys.argv):
            # Start the MQTT client
            client = mqtt_client.start_mqtt_client()
            mqtt_client.mqtt_client = client
            
            if client is None:
                logger.warning("Application started without MQTT functionality")
            else:
                logger.info("Application started with MQTT functionality")