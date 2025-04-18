# Create a new file: wyandata/mqtt_client.py
import paho.mqtt.client as mqtt
from django.conf import settings

def on_connect(client, userdata, flags, rc):
    print(f"Connected with result code {rc}")
    
    # Subscribe to topics here
    client.subscribe("weather/local")
    client.subscribe("solar/status")
    client.subscribe("system/status")

def on_message(client, userdata, msg):
    print(f"{msg.topic} {msg.payload}")
    # Process the incoming message here
    # You might want to send it to a WebSocket or save to DB

def start_mqtt_client():
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    
    # You might want to add authentication here
    # client.username_pw_set(username, password)
    
    # Connect to your MQTT broker
    client.connect("localhost", 1883, 60)
    
    # Start the loop
    client.loop_start()
    
    return client

# Save the client instance as a module-level variable
mqtt_client = None