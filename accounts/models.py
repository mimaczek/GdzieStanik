"""
Model użytkownika.

Zobacz docs/domain-model.md §3.4 — reguły U1–U5.
"""

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Domownik.

    Dziedziczy po AbstractUser, żeby móc rozszerzać model w przyszłości
    bez kosztownej migracji AUTH_USER_MODEL (ADR-0007).

    Reguły realizowane przez django.contrib.auth:
      U1 — brak publicznej rejestracji; konta zakłada createsuperuser
           albo istniejący użytkownik przez panel administracyjny
      U2 — brak ról; wszyscy zalogowani mają równe uprawnienia
      U3 — dezaktywacja przez is_active zamiast usuwania
      U4 — hasła wyłącznie jako hash Argon2id
      U5 — każdy widzi wszystkie domy; brak uprawnień per nieruchomość
    """

    display_name = models.CharField(
        "nazwa wyświetlana",
        max_length=100,
        blank=True,
        help_text="Imię pokazywane przy rzeczach, np. „Michał”. "
        "Puste — użyty zostanie login.",
    )

    class Meta:
        verbose_name = "domownik"
        verbose_name_plural = "domownicy"
        ordering = ["username"]

    def __str__(self) -> str:
        return self.display_name or self.username

    def save(self, *args, **kwargs) -> None:
        # Bez tego lista właścicieli pokazywałaby surowe loginy
        if not self.display_name:
            self.display_name = self.username
        super().save(*args, **kwargs)
