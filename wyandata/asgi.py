# wyandata/asgi.py
import os
import django
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from channels.db import database_sync_to_async
from django.db import close_old_connections

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'wyandata.settings')
django.setup()

# Custom middleware to close connections
class CloseConnectionsMiddleware:
    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        # Close connections before processing request
        await database_sync_to_async(close_old_connections)()
        try:
            # Process the request
            return await self.inner(scope, receive, send)
        finally:
            # Always close connections at the end
            await database_sync_to_async(close_old_connections)()

# Import your app's routing modules after django setup
import solar.routing
import system.routing
import weather.routing

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": CloseConnectionsMiddleware(
        AuthMiddlewareStack(
            URLRouter(
                solar.routing.websocket_urlpatterns +
                system.routing.websocket_urlpatterns +
                weather.routing.websocket_urlpatterns
            )
        )
    ),
})