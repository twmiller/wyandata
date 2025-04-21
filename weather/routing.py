from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    # Make sure the pattern matches exactly what your ASGI setup expects
    # If system and solar use paths starting with "/" or without one, be consistent
    # If they use paths with "^ws/..." then use that pattern
    re_path(r'^ws/weather/data/$', consumers.WeatherDataConsumer.as_asgi()),
]
