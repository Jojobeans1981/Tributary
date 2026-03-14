from rest_framework.permissions import BasePermission


class IsUpstreamStaff(BasePermission):
    """Allow access only to UPSTREAM_STAFF and PLATFORM_ADMIN users."""

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.role in ["UPSTREAM_STAFF", "PLATFORM_ADMIN"]
        )
