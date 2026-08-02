from django.utils import timezone

from attendance.utils.datetime_fmt import DISPLAY_TZ_NAME


class DarEsSalaamTimezoneMiddleware:
    """
    Activate East Africa Time (Africa/Dar_es_Salaam) for every request so
    Django timezone.localtime() and template date filters match the navbar
    clock and Recognition History.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        timezone.activate(DISPLAY_TZ_NAME)
        try:
            return self.get_response(request)
        finally:
            timezone.deactivate()
