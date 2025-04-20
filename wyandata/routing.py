from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
import system.routing
import solar.routing  # Add this import

application = ProtocolTypeRouter({
    'websocket': AuthMiddlewareStack(
        URLRouter(
            system.routing.websocket_urlpatterns +
            solar.routing.websocket_urlpatterns  # Add solar routes
        )
    ),
})
