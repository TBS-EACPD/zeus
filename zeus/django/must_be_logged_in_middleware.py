import urllib

from django.conf import settings
from django.http.response import HttpResponseRedirect


class MustBeLoggedInMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            return self.get_response(request)

        elif "/login" not in request.path.lower():
            qs_params = dict(next=request.build_absolute_uri())
            querystring = urllib.parse.urlencode(qs_params)
            return HttpResponseRedirect(f"{settings.LOGIN_URL}?{querystring}")

        else:
            return self.get_response(request)
