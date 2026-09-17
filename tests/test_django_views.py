import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "nse_insight.settings")

import django
django.setup()

from django.test import Client


def test_core_pages_render():
    client = Client()
    for url in ["/", "/stocks/", "/compare/", "/portfolio/", "/methodology/", "/api/market/"]:
        assert client.get(url).status_code == 200
