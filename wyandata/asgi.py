# wyandata/asgi.py
import os
import django
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'wyandata.settings')
django.setup()

# Import your app's routing modules after django setup
import solar.routing
import system.routing
import weather.routing

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(
            solar.routing.websocket_urlpatterns +
            system.routing.websocket_urlpatterns +
            weather.routing.websocket_urlpatterns
        )
    ),
})