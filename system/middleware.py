from django.db import close_old_connections

class CloseOldConnectionsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        close_old_connections()
        response = self.get_response(request)
        close_old_connections()
        return response
