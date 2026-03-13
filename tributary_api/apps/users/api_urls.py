from django.urls import path

from apps.users.views import MeView, UserProfileView

urlpatterns = [
    path("users/me/", MeView.as_view(), name="user-me"),
    path("users/<uuid:user_id>/", UserProfileView.as_view(), name="user-profile"),
]
