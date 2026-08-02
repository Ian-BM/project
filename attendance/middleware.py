from django.utils import timezone


class DarEsSalaamTimezoneMiddleware:
    """Activate Africa/Dar_es_Salaam for every request so templates and localtime() match the site clock."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        timezone.activate("Africa/Dar_es_Salaam")
        try:
            return self.get_response(request)
        finally:
            timezone.deactivate()
