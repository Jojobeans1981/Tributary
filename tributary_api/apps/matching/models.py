import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class ProblemStatement(models.Model):
    """Pre-seeded literacy problem statements. Integer PK for fast set operations."""

    id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=200)
    description = models.TextField()
    category = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    version = models.IntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return self.title


class UserProblemSelection(models.Model):
    """A user's selected problem statement (max 3 per user)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="problem_selections",
    )
    problem_statement = models.ForeignKey(
        ProblemStatement, on_delete=models.CASCADE
    )
    elaboration_text = models.TextField(max_length=280, blank=True, null=True)
    selected_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("user", "problem_statement")]

    def clean(self):
        """Layer 1: Model-level max-3 enforcement."""
        count = (
            UserProblemSelection.objects.filter(user=self.user)
            .exclude(pk=self.pk)
            .count()
        )
        if count >= 3:
            raise ValidationError(
                "You may select a maximum of 3 problem statements."
            )

    def __str__(self):
        return f"{self.user} → {self.problem_statement}"


class MatchScore(models.Model):
    """Precomputed match score between two users."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_a = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="match_scores_as_a",
    )
    user_b = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="match_scores_as_b",
    )
    demographic_score = models.IntegerField()
    problem_score = models.IntegerField()
    total_score = models.IntegerField()
    computed_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("user_a", "user_b")]
        indexes = [
            models.Index(fields=["-total_score"]),
            models.Index(fields=["user_a", "-total_score"]),
            models.Index(fields=["user_b", "-total_score"]),
        ]

    def __str__(self):
        return f"{self.user_a} ↔ {self.user_b}: {self.total_score}"


class Connection(models.Model):
    """Connection request state machine: PENDING → ACCEPTED/DECLINED/BLOCKED."""

    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    DECLINED = "DECLINED"
    BLOCKED = "BLOCKED"

    STATUS_CHOICES = [
        (PENDING, "Pending"),
        (ACCEPTED, "Accepted"),
        (DECLINED, "Declined"),
        (BLOCKED, "Blocked"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    requester = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_connections",
    )
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="received_connections",
    )
    status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default=PENDING
    )
    intro_message = models.TextField(max_length=500, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("requester", "recipient")]

    def __str__(self):
        return f"{self.requester} → {self.recipient} ({self.status})"
