# wyandata/asgi.py

import os
import django
from django.core.asgi import get_asgi_application

# Set up Django first
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'wyandata.settings')
django.setup()  # Set up Django explicitly before importing our routing

# Import the rest of the modules after Django is properly initialized
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from system import routing

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(
            routing.websocket_urlpatterns
        )
    ),
})