from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("apps.users.urls")),
    path("api/", include("apps.districts.urls")),
    path("api/", include("apps.users.api_urls")),
    # allauth URLs needed so send_confirmation can reverse account_confirm_email
    path("accounts/", include("allauth.urls")),
]
