"""
Trasy aplikacji inventory.

Formularze dodawania i przenoszenia powstaną w kroku 8
(architecture.md §11, §7).
"""

from django.urls import path

from . import views

app_name = "inventory"

urlpatterns = [
    path("", views.search, name="search"),
    path("item/<int:pk>/", views.item_detail, name="item_detail"),
    path("location/<int:pk>/", views.location_detail, name="location_detail"),
]
