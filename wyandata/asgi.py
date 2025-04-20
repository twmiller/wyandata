# wyandata/asgi.py
import os
import django
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from channels.security.websocket import AllowedHostsOriginValidator
import solar.routing
import system.routing  # Assuming you have system routing too

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'wyandata.settings')
django.setup()

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