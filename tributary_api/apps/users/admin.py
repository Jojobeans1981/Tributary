from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from apps.users.models import FerpaConsent, User


class FerpaConsentInline(admin.TabularInline):
    model = FerpaConsent
    extra = 0
    readonly_fields = ["id", "consented_at", "ip_address", "consent_text_version"]
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ["email", "get_full_name", "role", "district", "is_active", "date_joined"]
    list_filter = ["role", "is_active", "district__locale_type", "district__state"]
    search_fields = ["email", "first_name", "last_name"]
    ordering = ["-date_joined"]
    readonly_fields = ["id", "date_joined", "last_seen"]
    inlines = [FerpaConsentInline]

    fieldsets = (
        (None, {"fields": ("id", "email", "password")}),
        ("Personal info", {"fields": ("first_name", "last_name", "bio", "district")}),
        ("Roles & Preferences", {"fields": ("role", "email_preference")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Dates", {"fields": ("date_joined", "last_seen")}),
        ("Phase 4", {"fields": ("nudge_sent",)}),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "first_name", "last_name", "password1", "password2"),
        }),
    )

    actions = ["deactivate_selected", "activate_selected"]

    @admin.action(description="Deactivate selected users")
    def deactivate_selected(self, request, queryset):
        count = queryset.update(is_active=False)
        self.message_user(request, f"{count} user(s) deactivated.")

    @admin.action(description="Activate selected users")
    def activate_selected(self, request, queryset):
        count = queryset.update(is_active=True)
        self.message_user(request, f"{count} user(s) activated.")
