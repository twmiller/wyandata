# wyandata/mqtt_client.py
import paho.mqtt.client as mqtt
import logging

# Set up logging
logger = logging.getLogger(__name__)

def on_connect(client, userdata, flags, rc):
    logger.info(f"Connected to MQTT broker with result code {rc}")
    
    # Subscribe to topics here
    client.subscribe("weather/local")
    client.subscribe("solar/status")
    client.subscribe("system/status")

def on_message(client, userdata, msg):
    logger.info(f"Message received on {msg.topic}: {msg.payload}")
    # Process the incoming message here
    # You might want to send it to a WebSocket or save to DB

def on_disconnect(client, userdata, rc):
    if rc != 0:
        logger.warning(f"Unexpected MQTT disconnection with code {rc}. Will auto-reconnect.")

def start_mqtt_client():
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    client.on_disconnect = on_disconnect
    
    # You might want to add authentication here
    # client.username_pw_set(username, password)
    
    try:
        # Connect to your MQTT broker
        client.connect("localhost", 1883, 60)
        
        # Start the loop in a non-blocking way
        client.loop_start()
        logger.info("MQTT client started successfully")
        return client
    except ConnectionRefusedError:
        logger.warning("Could not connect to MQTT broker. MQTT functionality will be disabled.")
        return None
    except Exception as e:
        logger.error(f"Error starting MQTT client: {e}")
        return None

# Save the client instance as a module-level variable
mqtt_client = None