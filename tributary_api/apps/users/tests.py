import pytest
from django.test import RequestFactory
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from allauth.account.models import EmailAddress

from apps.districts.models import District
from apps.users.models import FerpaConsent, User


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user_data():
    return {
        "email": "testuser@example.com",
        "password": "TestPass123!",
        "first_name": "Test",
        "last_name": "User",
    }


@pytest.fixture
def verified_user(db):
    user = User.objects.create_user(
        email="verified@example.com",
        password="TestPass123!",
        first_name="Verified",
        last_name="User",
        is_active=True,
    )
    EmailAddress.objects.create(
        user=user, email=user.email, primary=True, verified=True
    )
    return user


@pytest.fixture
def consented_user(verified_user):
    FerpaConsent.objects.create(
        user=verified_user,
        ip_address="127.0.0.1",
        consent_text_version="1.0",
    )
    return verified_user


@pytest.fixture
def auth_client(api_client, consented_user):
    refresh = RefreshToken.for_user(consented_user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return api_client


@pytest.fixture
def district(db):
    return District.objects.create(
        nces_id="3600001",
        name="Springfield Public Schools",
        state="OH",
        locale_type="URBAN",
        enrollment=25000,
        frl_pct="45.00",
        ell_pct="12.00",
        data_vintage="2022-23",
    )


# ========== AUTH TESTS ==========

@pytest.mark.django_db
class TestRegister:
    def test_register_valid(self, api_client, user_data):
        res = api_client.post("/api/auth/register/", user_data, format="json")
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert User.objects.filter(email=user_data["email"]).exists()
        user = User.objects.get(email=user_data["email"])
        assert user.is_active is True
        # Email should be in allauth records
        assert EmailAddress.objects.filter(email=user_data["email"]).exists()

    def test_register_duplicate_email(self, api_client, user_data, verified_user):
        dup_data = {**user_data, "email": verified_user.email}
        res = api_client.post("/api/auth/register/", dup_data, format="json")
        assert res.status_code == 400
        data = res.json()
        assert data["success"] is False
        assert data["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.django_db
class TestVerifyEmail:
    def test_verify_bad_key(self, api_client):
        res = api_client.get("/api/auth/verify-email/bad-key-12345/")
        assert res.status_code == 400
        data = res.json()
        assert data["success"] is False


@pytest.mark.django_db
class TestLogin:
    def test_login_valid(self, api_client, verified_user):
        res = api_client.post(
            "/api/auth/login/",
            {"email": "verified@example.com", "password": "TestPass123!"},
            format="json",
        )
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert "access" in data["data"]
        assert "refresh" in data["data"]
        assert data["data"]["user"]["has_ferpa_consent"] is False

    def test_login_wrong_password(self, api_client, verified_user):
        res = api_client.post(
            "/api/auth/login/",
            {"email": "verified@example.com", "password": "WrongPass!"},
            format="json",
        )
        assert res.status_code == 400
        data = res.json()
        assert data["error"]["code"] == "AUTH_INVALID"

    def test_login_unverified(self, api_client, db):
        user = User.objects.create_user(
            email="unverified@example.com",
            password="TestPass123!",
            first_name="Un",
            last_name="Verified",
            is_active=True,
        )
        EmailAddress.objects.create(
            user=user, email=user.email, primary=True, verified=False
        )
        res = api_client.post(
            "/api/auth/login/",
            {"email": "unverified@example.com", "password": "TestPass123!"},
            format="json",
        )
        assert res.status_code == 400
        data = res.json()
        assert data["error"]["code"] == "AUTH_UNVERIFIED"

    def test_login_deactivated(self, api_client, db):
        user = User.objects.create_user(
            email="deactivated@example.com",
            password="TestPass123!",
            first_name="De",
            last_name="Activated",
            is_active=False,
        )
        EmailAddress.objects.create(
            user=user, email=user.email, primary=True, verified=True
        )
        res = api_client.post(
            "/api/auth/login/",
            {"email": "deactivated@example.com", "password": "TestPass123!"},
            format="json",
        )
        assert res.status_code == 400
        data = res.json()
        assert data["error"]["code"] == "AUTH_INACTIVE"


@pytest.mark.django_db
class TestTokenRefresh:
    def test_refresh_valid(self, api_client, verified_user):
        refresh = RefreshToken.for_user(verified_user)
        res = api_client.post(
            "/api/auth/token/refresh/",
            {"refresh": str(refresh)},
            format="json",
        )
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert "access" in data["data"]

    def test_refresh_blacklisted(self, api_client, verified_user):
        refresh = RefreshToken.for_user(verified_user)
        # Blacklist the token
        refresh.blacklist()
        res = api_client.post(
            "/api/auth/token/refresh/",
            {"refresh": str(refresh)},
            format="json",
        )
        assert res.status_code == 401
        data = res.json()
        assert data["error"]["code"] == "TOKEN_INVALID"


@pytest.mark.django_db
class TestPasswordReset:
    def test_password_reset_request(self, api_client, verified_user):
        res = api_client.post(
            "/api/auth/password/reset/",
            {"email": "verified@example.com"},
            format="json",
        )
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        # Always returns success regardless of email existence
        assert "If that email exists" in data["data"]["message"]

    def test_password_reset_nonexistent_email(self, api_client, db):
        res = api_client.post(
            "/api/auth/password/reset/",
            {"email": "nonexistent@example.com"},
            format="json",
        )
        assert res.status_code == 200
        assert res.json()["success"] is True


# ========== FERPA TESTS ==========

@pytest.mark.django_db
class TestFerpaConsent:
    def test_no_consent_returns_403(self, api_client, verified_user):
        refresh = RefreshToken.for_user(verified_user)
        api_client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}"
        )
        res = api_client.get("/api/users/me/")
        assert res.status_code == 403
        data = res.json()
        assert data["error"]["code"] == "FERPA_CONSENT_REQUIRED"

    def test_with_consent_returns_200(self, auth_client):
        res = auth_client.get("/api/users/me/")
        assert res.status_code == 200
        assert res.json()["success"] is True

    def test_post_consent(self, api_client, verified_user):
        refresh = RefreshToken.for_user(verified_user)
        api_client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}"
        )
        res = api_client.post(
            "/api/auth/consent/",
            {"consent_text_version": "1.0"},
            format="json",
        )
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert data["data"]["user"]["has_ferpa_consent"] is True

        consent = FerpaConsent.objects.get(user=verified_user)
        assert consent.consent_text_version == "1.0"
        assert consent.ip_address is not None

    def test_double_consent_returns_400(self, api_client, consented_user):
        refresh = RefreshToken.for_user(consented_user)
        api_client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}"
        )
        res = api_client.post(
            "/api/auth/consent/",
            {"consent_text_version": "1.0"},
            format="json",
        )
        assert res.status_code == 400
        assert res.json()["error"]["code"] == "CONSENT_EXISTS"


# ========== PROFILE TESTS ==========

@pytest.mark.django_db
class TestProfile:
    def test_me_no_bio(self, auth_client, consented_user):
        res = auth_client.get("/api/users/me/")
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["profile_completion_pct"] == 0

    def test_patch_bio_updates_completion(self, auth_client, consented_user):
        res = auth_client.patch(
            "/api/users/me/",
            {"bio": "I teach literacy in Ohio."},
            format="json",
        )
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["profile_completion_pct"] == 40

    def test_patch_bio_too_long(self, auth_client, consented_user):
        res = auth_client.patch(
            "/api/users/me/",
            {"bio": "x" * 501},
            format="json",
        )
        assert res.status_code == 400
        assert res.json()["error"]["code"] == "VALIDATION_ERROR"

    def test_patch_district_by_nces_id(self, auth_client, consented_user, district):
        res = auth_client.patch(
            "/api/users/me/",
            {"district": district.nces_id},
            format="json",
        )
        assert res.status_code == 200
        consented_user.refresh_from_db()
        assert consented_user.district == district

    def test_public_profile_no_email(self, auth_client, consented_user):
        res = auth_client.get(f"/api/users/{consented_user.id}/")
        assert res.status_code == 200
        data = res.json()["data"]
        assert "email" not in data

    def test_cannot_patch_other_user(self, api_client, consented_user, db):
        other = User.objects.create_user(
            email="other@example.com",
            password="TestPass123!",
            first_name="Other",
            last_name="User",
            is_active=True,
        )
        EmailAddress.objects.create(
            user=other, email=other.email, primary=True, verified=True
        )
        FerpaConsent.objects.create(
            user=other, ip_address="127.0.0.1", consent_text_version="1.0"
        )
        refresh = RefreshToken.for_user(other)
        api_client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}"
        )
        # PATCH on /api/users/{id}/ should not exist - it's a GET-only endpoint
        res = api_client.patch(
            f"/api/users/{consented_user.id}/",
            {"bio": "hacked"},
            format="json",
        )
        # Should be 405 Method Not Allowed since UserProfileView only has get()
        assert res.status_code == 405
