from django.contrib import admin

from apps.districts.models import District
from apps.districts.tasks import ingest_nces_data


@admin.register(District)
class DistrictAdmin(admin.ModelAdmin):
    list_display = ["name", "state", "locale_type", "enrollment", "frl_pct", "ell_pct", "data_vintage"]
    list_filter = ["locale_type", "state"]
    search_fields = ["name", "nces_id"]
    readonly_fields = ["id", "nces_id", "data_vintage", "created_at", "updated_at"]

    actions = ["trigger_nces_ingest"]

    @admin.action(description="Trigger NCES data ingest")
    def trigger_nces_ingest(self, request, queryset):
        ingest_nces_data.delay()
        self.message_user(request, "NCES ingest task has been queued.")
