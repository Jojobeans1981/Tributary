import io
import pytest
from decimal import Decimal
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from allauth.account.models import EmailAddress

from apps.districts.models import District
from apps.users.models import FerpaConsent, User


@pytest.fixture
def auth_client(db):
    user = User.objects.create_user(
        email="districtuser@example.com",
        password="TestPass123!",
        first_name="District",
        last_name="Tester",
        is_active=True,
    )
    EmailAddress.objects.create(
        user=user, email=user.email, primary=True, verified=True
    )
    FerpaConsent.objects.create(
        user=user, ip_address="127.0.0.1", consent_text_version="1.0"
    )
    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return client, user


@pytest.fixture
def sample_districts(db):
    districts = []
    data = [
        ("3600001", "Springfield Public Schools", "OH", "URBAN", 25000, "45.00", "12.00"),
        ("3600002", "Springfield Township Schools", "OH", "SUBURBAN", 8000, "22.00", "5.00"),
        ("1700001", "Chicago Public Schools", "IL", "URBAN", 340000, "45.00", "20.00"),
        ("0600001", "Los Angeles Unified", "CA", "URBAN", 600000, "40.00", "30.00"),
    ]
    for nces_id, name, state, locale, enroll, frl, ell in data:
        districts.append(
            District.objects.create(
                nces_id=nces_id,
                name=name,
                state=state,
                locale_type=locale,
                enrollment=enroll,
                frl_pct=frl,
                ell_pct=ell,
                data_vintage="2022-23",
            )
        )
    return districts


# ========== DISTRICT API TESTS ==========

@pytest.mark.django_db
class TestDistrictList:
    def test_search_spring(self, auth_client, sample_districts):
        client, _ = auth_client
        res = client.get("/api/districts/?search=spring")
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert len(data["data"]) == 2  # Springfield Public + Springfield Township
        assert len(data["data"]) <= 10

    def test_search_no_match(self, auth_client, sample_districts):
        client, _ = auth_client
        res = client.get("/api/districts/?search=zzznomatch")
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert len(data["data"]) == 0

    def test_search_with_state_filter(self, auth_client, sample_districts):
        client, _ = auth_client
        res = client.get("/api/districts/?search=spring&state=OH")
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert len(data["data"]) == 2
        for d in data["data"]:
            assert d["state"] == "OH"

    def test_district_detail_valid(self, auth_client, sample_districts):
        client, user = auth_client
        # Assign user to district
        user.district = sample_districts[0]
        user.save()
        res = client.get(f"/api/districts/{sample_districts[0].nces_id}/")
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["nces_id"] == "3600001"
        assert "members" in data
        # Verify no email in members
        for member in data["members"]:
            assert "email" not in member

    def test_district_detail_invalid(self, auth_client, sample_districts):
        client, _ = auth_client
        res = client.get("/api/districts/9999999/")
        assert res.status_code == 404


# ========== ETL TESTS ==========

@pytest.mark.django_db
class TestETL:
    def _run_etl(self, csv_content, **kwargs):
        """Helper to run ETL from a CSV string."""
        import os
        import tempfile
        from etl.ingest_nces import run_ingestion

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, encoding="utf-8"
        ) as f:
            f.write(csv_content)
            f.flush()
            path = f.name

        try:
            return run_ingestion(local_file=path, **kwargs)
        finally:
            os.unlink(path)

    def test_locale_11_urban(self, db):
        csv = "LEAID,LEA_NAME,STABR,ULOCALE,MEMBER,FRELCH,REDLCH,ELL\n1000001,Test City Large,NY,11,100,40,10,20\n"
        self._run_etl(csv)
        assert District.objects.get(nces_id="1000001").locale_type == "URBAN"

    def test_locale_12_urban(self, db):
        csv = "LEAID,LEA_NAME,STABR,ULOCALE,MEMBER,FRELCH,REDLCH,ELL\n1000002,Test City Mid,NY,12,100,40,10,20\n"
        self._run_etl(csv)
        assert District.objects.get(nces_id="1000002").locale_type == "URBAN"

    def test_locale_13_urban(self, db):
        csv = "LEAID,LEA_NAME,STABR,ULOCALE,MEMBER,FRELCH,REDLCH,ELL\n1000003,Test City Small,NY,13,100,40,10,20\n"
        self._run_etl(csv)
        assert District.objects.get(nces_id="1000003").locale_type == "URBAN"

    def test_locale_21_suburban(self, db):
        csv = "LEAID,LEA_NAME,STABR,ULOCALE,MEMBER,FRELCH,REDLCH,ELL\n2000001,Test Suburb Large,NY,21,100,40,10,20\n"
        self._run_etl(csv)
        assert District.objects.get(nces_id="2000001").locale_type == "SUBURBAN"

    def test_locale_22_suburban(self, db):
        csv = "LEAID,LEA_NAME,STABR,ULOCALE,MEMBER,FRELCH,REDLCH,ELL\n2000002,Test Suburb Mid,NY,22,100,40,10,20\n"
        self._run_etl(csv)
        assert District.objects.get(nces_id="2000002").locale_type == "SUBURBAN"

    def test_locale_23_suburban(self, db):
        csv = "LEAID,LEA_NAME,STABR,ULOCALE,MEMBER,FRELCH,REDLCH,ELL\n2000003,Test Suburb Small,NY,23,100,40,10,20\n"
        self._run_etl(csv)
        assert District.objects.get(nces_id="2000003").locale_type == "SUBURBAN"

    def test_locale_31_town(self, db):
        csv = "LEAID,LEA_NAME,STABR,ULOCALE,MEMBER,FRELCH,REDLCH,ELL\n3000001,Test Town Fringe,NY,31,100,40,10,20\n"
        self._run_etl(csv)
        assert District.objects.get(nces_id="3000001").locale_type == "TOWN"

    def test_locale_32_town(self, db):
        csv = "LEAID,LEA_NAME,STABR,ULOCALE,MEMBER,FRELCH,REDLCH,ELL\n3000002,Test Town Distant,NY,32,100,40,10,20\n"
        self._run_etl(csv)
        assert District.objects.get(nces_id="3000002").locale_type == "TOWN"

    def test_locale_33_town(self, db):
        csv = "LEAID,LEA_NAME,STABR,ULOCALE,MEMBER,FRELCH,REDLCH,ELL\n3000003,Test Town Remote,NY,33,100,40,10,20\n"
        self._run_etl(csv)
        assert District.objects.get(nces_id="3000003").locale_type == "TOWN"

    def test_locale_41_rural(self, db):
        csv = "LEAID,LEA_NAME,STABR,ULOCALE,MEMBER,FRELCH,REDLCH,ELL\n4000001,Test Rural Fringe,NY,41,100,40,10,20\n"
        self._run_etl(csv)
        assert District.objects.get(nces_id="4000001").locale_type == "RURAL"

    def test_locale_42_rural(self, db):
        csv = "LEAID,LEA_NAME,STABR,ULOCALE,MEMBER,FRELCH,REDLCH,ELL\n4000002,Test Rural Distant,NY,42,100,40,10,20\n"
        self._run_etl(csv)
        assert District.objects.get(nces_id="4000002").locale_type == "RURAL"

    def test_locale_43_rural(self, db):
        csv = "LEAID,LEA_NAME,STABR,ULOCALE,MEMBER,FRELCH,REDLCH,ELL\n4000003,Test Rural Remote,NY,43,100,40,10,20\n"
        self._run_etl(csv)
        assert District.objects.get(nces_id="4000003").locale_type == "RURAL"

    def test_frl_pct_calculation(self, db):
        csv = "LEAID,LEA_NAME,STABR,ULOCALE,MEMBER,FRELCH,REDLCH,ELL\n5000001,FRL Test,NY,11,200,60,40,10\n"
        self._run_etl(csv)
        d = District.objects.get(nces_id="5000001")
        # (60 + 40) / 200 * 100 = 50.00
        assert d.frl_pct == Decimal("50.00")

    def test_frl_pct_zero_member(self, db):
        csv = "LEAID,LEA_NAME,STABR,ULOCALE,MEMBER,FRELCH,REDLCH,ELL\n5000002,Zero Test,NY,11,0,0,0,0\n"
        self._run_etl(csv)
        d = District.objects.get(nces_id="5000002")
        assert d.frl_pct == Decimal("0.00")

    def test_ell_pct_zero_member(self, db):
        csv = "LEAID,LEA_NAME,STABR,ULOCALE,MEMBER,FRELCH,REDLCH,ELL\n5000003,ELL Zero,NY,11,0,0,0,0\n"
        self._run_etl(csv)
        d = District.objects.get(nces_id="5000003")
        assert d.ell_pct == Decimal("0.00")

    def test_upsert_no_duplicates(self, db):
        csv = "LEAID,LEA_NAME,STABR,ULOCALE,MEMBER,FRELCH,REDLCH,ELL\n6000001,Upsert Test,NY,11,100,40,10,20\n"
        self._run_etl(csv)
        assert District.objects.filter(nces_id="6000001").count() == 1
        self._run_etl(csv)
        assert District.objects.filter(nces_id="6000001").count() == 1
