from rest_framework import serializers

from apps.matching.models import (
    Connection,
    ProblemStatement,
    UserProblemSelection,
)


class ProblemStatementSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProblemStatement
        fields = ["id", "title", "description", "category", "version"]


class ProblemStatementBriefSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProblemStatement
        fields = ["id", "title", "category"]


class UserProblemSelectionSerializer(serializers.ModelSerializer):
    problem_statement = ProblemStatementBriefSerializer(read_only=True)

    class Meta:
        model = UserProblemSelection
        fields = ["id", "problem_statement", "elaboration_text", "selected_at"]


class CreateSelectionSerializer(serializers.Serializer):
    problem_statement_id = serializers.IntegerField()
    elaboration_text = serializers.CharField(
        max_length=280, required=False, allow_blank=True, default=""
    )

    def validate(self, attrs):
        """Layer 2: Serializer-level max-3 enforcement."""
        user = self.context["request"].user
        if UserProblemSelection.objects.filter(user=user).count() >= 3:
            raise serializers.ValidationError({
                "code": "SELECTION_LIMIT_EXCEEDED",
                "message": "You have already selected 3 problem statements.",
            })
        return attrs


class UpdateSelectionSerializer(serializers.Serializer):
    elaboration_text = serializers.CharField(
        max_length=280, required=True, allow_blank=True
    )


class ConnectionSerializer(serializers.ModelSerializer):
    requester_name = serializers.SerializerMethodField()
    recipient_name = serializers.SerializerMethodField()

    class Meta:
        model = Connection
        fields = [
            "id",
            "requester",
            "recipient",
            "requester_name",
            "recipient_name",
            "status",
            "intro_message",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "requester",
            "status",
            "created_at",
            "updated_at",
        ]

    def get_requester_name(self, obj):
        return obj.requester.get_full_name() if obj.requester else ""

    def get_recipient_name(self, obj):
        return obj.recipient.get_full_name() if obj.recipient else ""


class CreateConnectionSerializer(serializers.Serializer):
    recipient_id = serializers.UUIDField()
    intro_message = serializers.CharField(
        max_length=500, required=False, allow_blank=True, default=""
    )


class UpdateConnectionSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=["ACCEPTED", "DECLINED"])
