from django.http import JsonResponse
from django.urls import include, path


def health(request):
    return JsonResponse({
        "status": "ok",
        "service": "nse-insight",
    })


urlpatterns = [
    path("health/", health, name="health"),
    path("", include("market.urls")),
]
