"""Serializers for staff moderation endpoints."""
from rest_framework import serializers


class StaffDirectMessageSerializer(serializers.Serializer):
    recipient_id = serializers.UUIDField()
    body = serializers.CharField(max_length=5000)


class StaffBroadcastSerializer(serializers.Serializer):
    body = serializers.CharField(max_length=5000)
    recipient_ids = serializers.ListField(
        child=serializers.UUIDField(),
        min_length=1,
    )
