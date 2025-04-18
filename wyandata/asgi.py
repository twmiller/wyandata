# wyandata/asgi.py
import os
import django
from django.core.asgi import get_asgi_application

# Set up Django first
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'wyandata.settings')
django.setup()

# Import the rest after Django is initialized
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from system import routing  # Make sure this import works

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(
            routing.websocket_urlpatterns
        )
    ),
})