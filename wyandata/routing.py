from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator

# Import your app's routing modules
import solar.routing
import system.routing
import weather.routing  # Add this line

application = ProtocolTypeRouter({
    'websocket': AllowedHostsOriginValidator(
        AuthMiddlewareStack(
            URLRouter(
                solar.routing.websocket_urlpatterns +
                system.routing.websocket_urlpatterns +
                weather.routing.websocket_urlpatterns  # Add this line
            )
        )
    ),
})
