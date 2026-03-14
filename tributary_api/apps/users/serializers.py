from rest_framework import serializers

from apps.districts.serializers import DistrictSerializer
from apps.users.models import FerpaConsent, User


def _profile_completion_pct(user) -> int:
    score = 0
    if user.bio and user.bio.strip():
        score += 40
    if user.district_id:
        score += 30
    selections = user.problem_selections.count()
    if selections >= 1:
        score += 20
    if selections >= 2:
        score += 10
    return min(score, 100)


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    first_name = serializers.CharField(max_length=100)
    last_name = serializers.CharField(max_length=100)

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value.lower()


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class ConsentSerializer(serializers.Serializer):
    consent_text_version = serializers.CharField(max_length=10, default="1.0")


class PasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True, min_length=8)


class UserSerializer(serializers.ModelSerializer):
    has_ferpa_consent = serializers.SerializerMethodField()
    has_district = serializers.SerializerMethodField()
    profile_completion_pct = serializers.SerializerMethodField()
    problem_selection_count = serializers.SerializerMethodField()
    district = DistrictSerializer(read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "role",
            "bio",
            "district",
            "profile_completion_pct",
            "problem_selection_count",
            "has_ferpa_consent",
            "has_district",
            "email_preference",
        ]
        read_only_fields = ["id", "email", "role"]

    def get_has_ferpa_consent(self, obj):
        return hasattr(obj, "ferpa_consent")

    def get_has_district(self, obj):
        return obj.district_id is not None

    def get_profile_completion_pct(self, obj):
        return _profile_completion_pct(obj)

    def get_problem_selection_count(self, obj):
        return obj.problem_selections.count()


class PublicUserSerializer(serializers.ModelSerializer):
    district = DistrictSerializer(read_only=True)

    class Meta:
        model = User
        fields = ["id", "first_name", "last_name", "role", "bio", "district"]


class UserUpdateSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=100, required=False)
    last_name = serializers.CharField(max_length=100, required=False)
    bio = serializers.CharField(max_length=500, required=False, allow_blank=True)
    district = serializers.CharField(max_length=7, required=False, allow_null=True)

    def validate_bio(self, value):
        if len(value) > 500:
            raise serializers.ValidationError("Bio must be 500 characters or fewer.")
        return value


class LoginResponseUserSerializer(serializers.ModelSerializer):
    has_ferpa_consent = serializers.SerializerMethodField()
    has_district = serializers.SerializerMethodField()
    has_problem_selections = serializers.SerializerMethodField()
    profile_completion_pct = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "role",
            "has_ferpa_consent",
            "has_district",
            "has_problem_selections",
            "profile_completion_pct",
        ]

    def get_has_ferpa_consent(self, obj):
        return hasattr(obj, "ferpa_consent")

    def get_has_district(self, obj):
        return obj.district_id is not None

    def get_has_problem_selections(self, obj):
        return obj.problem_selections.exists()

    def get_profile_completion_pct(self, obj):
        return _profile_completion_pct(obj)
