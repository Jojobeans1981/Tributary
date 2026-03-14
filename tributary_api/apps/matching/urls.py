from django.urls import path

from apps.matching.community_views import (
    ChannelListView,
    ChannelMembersView,
    CommunityListView,
    MatchFeedbackCreateView,
    MatchFeedbackListView,
)
from apps.matching.views import (
    ConnectionBlockView,
    ConnectionDetailView,
    ConnectionListCreateView,
    MatchFeedView,
    ProblemListView,
    SelectionDetailView,
    SelectionListCreateView,
)

urlpatterns = [
    # Problem statements
    path("problems/", ProblemListView.as_view()),
    # User problem selections
    path(
        "users/me/problem-selections/",
        SelectionListCreateView.as_view(),
    ),
    path(
        "users/me/problem-selections/<uuid:selection_id>/",
        SelectionDetailView.as_view(),
    ),
    # Match feed
    path("matches/", MatchFeedView.as_view()),
    # Connections
    path("connections/", ConnectionListCreateView.as_view()),
    path("connections/<uuid:connection_id>/", ConnectionDetailView.as_view()),
    path(
        "connections/<uuid:connection_id>/block/",
        ConnectionBlockView.as_view(),
    ),
    # Community directory
    path("community/", CommunityListView.as_view()),
    # Channels
    path("channels/", ChannelListView.as_view()),
    path("channels/<int:problem_id>/members/", ChannelMembersView.as_view()),
    # Match feedback
    path("feedback/", MatchFeedbackCreateView.as_view()),
    path("feedback/my/", MatchFeedbackListView.as_view()),
]
