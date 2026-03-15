from django.contrib.auth import authenticate
from django.utils import timezone
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError

from allauth.account.models import EmailAddress

from apps.users.models import FerpaConsent, User
from apps.users.serializers import (
    ConsentSerializer,
    LoginResponseUserSerializer,
    LoginSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetSerializer,
    PublicUserSerializer,
    RegisterSerializer,
    UserSerializer,
    UserUpdateSerializer,
)
from apps.users.utils import err, ok


class RegisterView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return err(
                "VALIDATION_ERROR",
                serializer.errors,
            )

        data = serializer.validated_data
        user = User.objects.create_user(
            email=data["email"],
            password=data["password"],
            first_name=data["first_name"],
            last_name=data["last_name"],
            is_active=True,
        )

        # Auto-verify email — skip SendGrid email verification for now
        EmailAddress.objects.create(
            user=user,
            email=user.email,
            primary=True,
            verified=True,
        )

        return ok({"message": "Account created. You can now log in."})


class VerifyEmailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, key):
        from allauth.account.models import EmailConfirmationHMAC

        try:
            confirmation = EmailConfirmationHMAC.from_key(key)
        except Exception:
            confirmation = None

        if confirmation is None:
            return err("VERIFICATION_FAILED", "Invalid or expired verification link.")

        confirmation.confirm(request)
        user = confirmation.email_address.user
        user.is_active = True
        user.save(update_fields=["is_active"])

        return ok({"message": "Email verified. Please accept the privacy agreement."})


class LoginView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return err("VALIDATION_ERROR", serializer.errors)

        email = serializer.validated_data["email"].lower()
        password = serializer.validated_data["password"]

        # Check if user exists
        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            return err("AUTH_INVALID", "Invalid email or password.")

        # Check if email is verified
        email_address = EmailAddress.objects.filter(
            user=user, email__iexact=email
        ).first()
        if email_address and not email_address.verified:
            return err("AUTH_UNVERIFIED", "Please verify your email before logging in.")

        # Check if user is active
        if not user.is_active:
            return err("AUTH_INACTIVE", "This account has been deactivated.")

        # Authenticate
        authenticated_user = authenticate(request, email=email, password=password)
        if authenticated_user is None:
            return err("AUTH_INVALID", "Invalid email or password.")

        # Update last_seen
        authenticated_user.last_seen = timezone.now()
        authenticated_user.save(update_fields=["last_seen"])

        # Generate tokens
        refresh = RefreshToken.for_user(authenticated_user)

        user_data = LoginResponseUserSerializer(authenticated_user).data

        return ok({
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": user_data,
        })


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return err("VALIDATION_ERROR", "Refresh token is required.")

        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except TokenError:
            return err("TOKEN_INVALID", "Token is invalid or already blacklisted.", status=401)

        return ok({"message": "Logged out."})


class TokenRefreshView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return err("VALIDATION_ERROR", "Refresh token is required.")

        try:
            token = RefreshToken(refresh_token)
            new_access = str(token.access_token)
        except TokenError:
            return err("TOKEN_INVALID", "Token is invalid or expired.", status=401)

        return ok({"access": new_access})


class PasswordResetView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetSerializer(data=request.data)
        if not serializer.is_valid():
            return err("VALIDATION_ERROR", serializer.errors)

        # Always return success — never reveal whether email is registered
        email = serializer.validated_data["email"]
        try:
            user = User.objects.get(email__iexact=email)
            # Use Django's built-in password reset
            from django.contrib.auth.tokens import default_token_generator
            from django.utils.http import urlsafe_base64_encode
            from django.utils.encoding import force_bytes
            from django.core.mail import send_mail
            from django.conf import settings

            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            reset_url = f"{settings.FRONTEND_URL}/reset-password?uid={uid}&token={token}"

            send_mail(
                subject="TRIBUTARY — Password Reset",
                message=f"Click here to reset your password: {reset_url}",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=True,
            )
        except User.DoesNotExist:
            pass

        return ok({"message": "If that email exists, a reset link was sent."})


class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        if not serializer.is_valid():
            return err("VALIDATION_ERROR", serializer.errors)

        from django.contrib.auth.tokens import default_token_generator
        from django.utils.http import urlsafe_base64_decode

        try:
            uid = urlsafe_base64_decode(serializer.validated_data["uid"]).decode()
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return err("RESET_INVALID", "Invalid reset link.")

        if not default_token_generator.check_token(user, serializer.validated_data["token"]):
            return err("RESET_INVALID", "Invalid or expired reset link.")

        user.set_password(serializer.validated_data["new_password"])
        user.save()

        return ok({"message": "Password updated."})


class ConsentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if hasattr(request.user, "ferpa_consent"):
            return err("CONSENT_EXISTS", "You have already accepted the privacy agreement.")

        serializer = ConsentSerializer(data=request.data)
        if not serializer.is_valid():
            return err("VALIDATION_ERROR", serializer.errors)

        # Get IP address, handling X-Forwarded-For for Render proxy
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip_address = x_forwarded_for.split(",")[0].strip()
        else:
            ip_address = request.META.get("REMOTE_ADDR", "0.0.0.0")

        FerpaConsent.objects.create(
            user=request.user,
            ip_address=ip_address,
            consent_text_version=serializer.validated_data.get("consent_text_version", "1.0"),
        )

        # Refresh user from DB to include ferpa_consent relation
        request.user.refresh_from_db()
        user_data = UserSerializer(request.user).data

        return ok({"user": user_data})


class MeView(APIView):
    """GET /api/users/me/ and PATCH /api/users/me/"""

    def get(self, request):
        serializer = UserSerializer(request.user)
        return ok(serializer.data)

    def patch(self, request):
        serializer = UserUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return err("VALIDATION_ERROR", serializer.errors)

        user = request.user
        data = serializer.validated_data

        if "first_name" in data:
            user.first_name = data["first_name"]
        if "last_name" in data:
            user.last_name = data["last_name"]
        if "bio" in data:
            user.bio = data["bio"]
        if "district" in data:
            if data["district"] is None:
                user.district = None
            else:
                from apps.districts.models import District
                try:
                    district = District.objects.get(nces_id=data["district"])
                    user.district = district
                except District.DoesNotExist:
                    return err("VALIDATION_ERROR", "District not found.")

        user.save()
        return ok(UserSerializer(user).data)


class UserProfileView(APIView):
    """GET /api/users/{id}/ — public profile, no email exposed."""

    def get(self, request, user_id):
        try:
            user = User.objects.get(pk=user_id, is_active=True)
        except (User.DoesNotExist, ValueError):
            return err("NOT_FOUND", "User not found.", status=404)

        serializer = PublicUserSerializer(user)
        return ok(serializer.data)
