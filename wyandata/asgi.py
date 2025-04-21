# wyandata/asgi.py
import os
from django.core.asgi import get_asgi_application
from channels.routing import get_default_application
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'wyandata.settings')
django.setup()

# Use the ASGI application with Channels routing
application = get_default_application()