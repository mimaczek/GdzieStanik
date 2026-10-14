"""
Trasy aplikacji inventory (architecture.md §7).
"""

from django.urls import path

from . import views

app_name = "inventory"

urlpatterns = [
    path("", views.search, name="search"),
    path("add/", views.add_item, name="add_item"),
    path("item/<int:pk>/", views.item_detail, name="item_detail"),
    path("item/<int:pk>/move/", views.move_item, name="move_item"),
    path("location/<int:pk>/", views.location_detail, name="location_detail"),
    path(
        "location/<int:pk>/children/",
        views.location_children,
        name="location_children",
    ),
]
