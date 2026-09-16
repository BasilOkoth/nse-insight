from django.urls import path
from . import views

app_name = "market"
urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("stocks/", views.stock_screener, name="stocks"),
    path("stocks/<str:ticker>/", views.stock_detail, name="stock_detail"),
    path("portfolio/", views.portfolio, name="portfolio"),
    path("methodology/", views.methodology, name="methodology"),
    path("refresh/", views.refresh_market, name="refresh"),
    path("api/market/", views.market_api, name="market_api"),
]
