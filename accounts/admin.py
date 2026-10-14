from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ["username", "display_name", "is_active", "is_staff"]
    list_filter = ["is_active", "is_staff"]
    search_fields = ["username", "display_name"]
    ordering = ["username"]

    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("Dane osobowe", {"fields": ("display_name", "email")}),
        (
            "Uprawnienia",
            {
                "fields": ("is_active", "is_staff", "is_superuser"),
                "description": "Reguła U2: wszyscy zalogowani mają równe "
                "uprawnienia w aplikacji. Pola poniżej dotyczą wyłącznie "
                "dostępu do tego panelu.",
            },
        ),
        ("Daty", {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("username", "display_name", "password1", "password2"),
            },
        ),
    )
