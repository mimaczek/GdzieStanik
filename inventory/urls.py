"""
Trasy aplikacji inventory.

Pełny zestaw powstanie w krokach 7–8 (architecture.md §11).
Na razie tylko strona startowa, żeby zweryfikować szkielet.
"""

from django.urls import path

from . import views

app_name = "inventory"

urlpatterns = [
    path("", views.search, name="search"),
]
