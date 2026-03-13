"""
District model for TRIBUTARY.

NCES locale code -> locale_type mapping:
    NCES codes 11, 12, 13 (City - Large, Midsize, Small)       -> URBAN
    NCES codes 21, 22, 23 (Suburb - Large, Midsize, Small)     -> SUBURBAN
    NCES codes 31, 32, 33 (Town - Fringe, Distant, Remote)     -> TOWN
    NCES codes 41, 42, 43 (Rural - Fringe, Distant, Remote)    -> RURAL
"""
import uuid

from django.db import models


NCES_LOCALE_MAP = {
    "11": "URBAN",
    "12": "URBAN",
    "13": "URBAN",
    "21": "SUBURBAN",
    "22": "SUBURBAN",
    "23": "SUBURBAN",
    "31": "TOWN",
    "32": "TOWN",
    "33": "TOWN",
    "41": "RURAL",
    "42": "RURAL",
    "43": "RURAL",
}


class District(models.Model):
    class LocaleType(models.TextChoices):
        URBAN = "URBAN", "Urban"
        SUBURBAN = "SUBURBAN", "Suburban"
        RURAL = "RURAL", "Rural"
        TOWN = "TOWN", "Town"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nces_id = models.CharField(max_length=7, unique=True)
    name = models.CharField(max_length=200)
    state = models.CharField(max_length=2)
    locale_type = models.CharField(
        max_length=10,
        choices=LocaleType.choices,
    )
    enrollment = models.PositiveIntegerField()
    frl_pct = models.DecimalField(max_digits=5, decimal_places=2)
    ell_pct = models.DecimalField(max_digits=5, decimal_places=2)
    data_vintage = models.CharField(max_length=10)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.state})"
