from django.urls import path

from apps.matching.community_views import (
    FeaturedMemberDeleteView,
    FeaturedMemberListCreateView,
)
from apps.staff.analytics import StaffAnalyticsExportView, StaffAnalyticsView
from apps.staff.taxonomy import (
    TaxonomyDetailView,
    TaxonomyListCreateView,
    TaxonomyRetireView,
)
from apps.staff.views import (
    StaffBroadcastView,
    StaffConversationJoinView,
    StaffConversationListView,
    StaffDirectMessageView,
    StaffMessageDeleteView,
    StaffSuspendUserView,
)

urlpatterns = [
    # Messaging moderation
    path("conversations/", StaffConversationListView.as_view()),
    path(
        "conversations/<uuid:conversation_id>/join/",
        StaffConversationJoinView.as_view(),
    ),
    path("messages/<uuid:message_id>/", StaffMessageDeleteView.as_view()),
    path("messages/", StaffDirectMessageView.as_view()),
    path("broadcast/", StaffBroadcastView.as_view()),
    path("users/<uuid:user_id>/suspend/", StaffSuspendUserView.as_view()),
    # Featured members
    path("featured/", FeaturedMemberListCreateView.as_view()),
    path("featured/<uuid:featured_id>/", FeaturedMemberDeleteView.as_view()),
    # Analytics
    path("analytics/", StaffAnalyticsView.as_view()),
    path("analytics/export/", StaffAnalyticsExportView.as_view()),
    # Taxonomy management
    path("taxonomy/", TaxonomyListCreateView.as_view()),
    path("taxonomy/<int:statement_id>/", TaxonomyDetailView.as_view()),
    path("taxonomy/<int:statement_id>/retire/", TaxonomyRetireView.as_view()),
]
