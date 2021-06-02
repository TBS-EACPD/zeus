from django.conf import settings
from django.db import connections
from django.db.models import signals


def mark_whodid(user, sender, instance, **kwargs):
    if hasattr(sender, "edited_by"):
        instance.edited_by = user


class WhodidMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method not in ("GET", "HEAD", "OPTIONS", "TRACE"):
            if hasattr(request, "user") and request.user.is_authenticated:
                user = request.user
            else:
                user = None

            def wrapped_mark_whodid(*args, **kwargs):
                return mark_whodid(user, *args, **kwargs)

            signals.pre_save.connect(
                wrapped_mark_whodid, dispatch_uid=(self.__class__, request,), weak=False
            )

        response = self.get_response(request)

        signals.pre_save.disconnect(dispatch_uid=(self.__class__, request,))

        return response
