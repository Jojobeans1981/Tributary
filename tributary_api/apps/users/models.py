import uuid

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required.")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    class Role(models.TextChoices):
        MEMBER = "MEMBER", "Member"
        DISTRICT_ADMIN = "DISTRICT_ADMIN", "District Admin"
        UPSTREAM_STAFF = "UPSTREAM_STAFF", "Upstream Staff"
        PLATFORM_ADMIN = "PLATFORM_ADMIN", "Platform Admin"

    class EmailPreference(models.TextChoices):
        IMMEDIATE = "IMMEDIATE", "Immediate"
        DAILY_DIGEST = "DAILY_DIGEST", "Daily Digest"
        OFF = "OFF", "Off"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.MEMBER,
    )
    bio = models.TextField(max_length=500, blank=True, default="")
    district = models.ForeignKey(
        "districts.District",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="members",
    )
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)
    last_seen = models.DateTimeField(null=True, blank=True)
    nudge_sent = models.BooleanField(default=False)
    email_preference = models.CharField(
        max_length=20,
        choices=EmailPreference.choices,
        default=EmailPreference.IMMEDIATE,
    )

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        indexes = [
            models.Index(fields=["is_active", "role"]),
            models.Index(fields=["is_active", "date_joined"]),
        ]

    def __str__(self):
        return self.email

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def get_short_name(self):
        return self.first_name


class FerpaConsent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="ferpa_consent",
    )
    consented_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(protocol="both", unpack_ipv4=True)
    consent_text_version = models.CharField(max_length=10, default="1.0")

    def __str__(self):
        return f"FERPA consent for {self.user.email} (v{self.consent_text_version})"
