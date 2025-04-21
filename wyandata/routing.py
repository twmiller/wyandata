from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator

# Import app routing modules
import solar.routing
import system.routing
import weather.routing  # Make sure this import is present

application = ProtocolTypeRouter({
    'websocket': AllowedHostsOriginValidator(
        AuthMiddlewareStack(
            URLRouter(
                # Include all your app's websocket URL patterns
                solar.routing.websocket_urlpatterns +
                system.routing.websocket_urlpatterns +
                weather.routing.websocket_urlpatterns  # Make sure this is included
            )
        )
    ),
})
