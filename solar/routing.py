from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    # Make sure the path format matches your project structure
    re_path(r'^ws/solar/data/$', consumers.SolarDataConsumer.as_asgi()),
]
