# wyandata/asgi.py
import os
import django

# Set up Django first, before any other imports
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'wyandata.settings')
django.setup()

# Now import channels and other Django components
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from channels.security.websocket import AllowedHostsOriginValidator

# Only import app routing after Django is set up
import solar.routing
import system.routing  # Assuming you have system routing too

# Create the ASGI application
application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AllowedHostsOriginValidator(
        AuthMiddlewareStack(
            URLRouter(
                solar.routing.websocket_urlpatterns +
                system.routing.websocket_urlpatterns  # Include both routing patterns
            )
        )
    ),
})