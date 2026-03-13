from rest_framework.permissions import BasePermission


class HasFerpaConsent(BasePermission):
    message = {
        "success": False,
        "error": {
            "code": "FERPA_CONSENT_REQUIRED",
            "message": "You must accept the privacy agreement before continuing."
        }
    }

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return True  # unauthenticated requests handled by IsAuthenticated
        return hasattr(request.user, "ferpa_consent")
