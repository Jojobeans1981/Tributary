from django.urls import path

from apps.users.views import (
    ConsentView,
    LoginView,
    LogoutView,
    PasswordResetConfirmView,
    PasswordResetView,
    RegisterView,
    TokenRefreshView,
    VerifyEmailView,
)

urlpatterns = [
    path("register/", RegisterView.as_view(), name="auth-register"),
    path("login/", LoginView.as_view(), name="auth-login"),
    path("logout/", LogoutView.as_view(), name="auth-logout"),
    path("token/refresh/", TokenRefreshView.as_view(), name="auth-token-refresh"),
    path("verify-email/<str:key>/", VerifyEmailView.as_view(), name="auth-verify-email"),
    path("password/reset/", PasswordResetView.as_view(), name="auth-password-reset"),
    path("password/reset/confirm/", PasswordResetConfirmView.as_view(), name="auth-password-reset-confirm"),
    path("consent/", ConsentView.as_view(), name="auth-consent"),
]
