# messaging/routing.py
from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/chat/(?P<conversation_id>\d+)/$', consumers.ChatConsumer.as_asgi()),
] # This routing file defines the WebSocket URL pattern for the chat consumer, which handles real-time messaging for a specific conversation thread.

# kredhaus/asgi.py
import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.middleware import BaseMiddleware
from messaging.routing import websocket_urlpatterns

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'kredhaus.settings')

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": URLRouter(websocket_urlpatterns),
}) # This ASGI configuration sets up the application to route HTTP requests to Django's standard ASGI application, and WebSocket connections to the URL patterns defined in messaging.routing. 
# It serves as the entry point for both types of connections.