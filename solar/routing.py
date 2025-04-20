from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/solar/data/$', consumers.SolarDataConsumer.as_asgi()),
]
