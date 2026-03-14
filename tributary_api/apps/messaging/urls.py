from django.urls import path

from apps.messaging.views import (
    ConversationListCreateView,
    ConversationMessagesView,
    ConversationReadView,
    FileUploadView,
    NotificationListView,
    NotificationReadAllView,
)

urlpatterns = [
    path("conversations/", ConversationListCreateView.as_view()),
    path(
        "conversations/<uuid:conversation_id>/messages/",
        ConversationMessagesView.as_view(),
    ),
    path(
        "conversations/<uuid:conversation_id>/read/",
        ConversationReadView.as_view(),
    ),
    path("upload/", FileUploadView.as_view()),
    path("notifications/", NotificationListView.as_view()),
    path("notifications/read-all/", NotificationReadAllView.as_view()),
]
