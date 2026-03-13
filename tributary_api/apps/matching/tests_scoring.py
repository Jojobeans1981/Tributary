"""
Unit tests for the pure-Python scoring engine.
No Django imports — these test scoring.py in isolation.
"""
from apps.matching.scoring import (
    DistrictProfile,
    MatchScoreResult,
    UserMatchProfile,
    compute_match_score,
)


def _make_profile(
    user_id="aaaaaaaa-0000-0000-0000-000000000001",
    locale_type="URBAN",
    enrollment=10000,
    frl_pct=30.0,
    ell_pct=10.0,
    problem_ids=None,
):
    return UserMatchProfile(
        user_id=user_id,
        district=DistrictProfile(
            locale_type=locale_type,
            enrollment=enrollment,
            frl_pct=frl_pct,
            ell_pct=ell_pct,
        ),
        problem_ids=problem_ids or [],
    )


class TestScoringEngine:
    def test_zero_problems_max_demo(self):
        """Same locale/band/frl/ell, no shared problems → total=40."""
        a = _make_profile(user_id="aaaaaaaa-0000-0000-0000-000000000001")
        b = _make_profile(user_id="bbbbbbbb-0000-0000-0000-000000000002")
        result = compute_match_score(a, b)
        assert result.demographic_score == 40
        assert result.problem_score == 0
        assert result.total_score == 40

    def test_all_components_max(self):
        """Same locale/band/frl/ell, 3 shared → total=100."""
        a = _make_profile(
            user_id="aaaaaaaa-0000-0000-0000-000000000001",
            problem_ids=[1, 2, 3],
        )
        b = _make_profile(
            user_id="bbbbbbbb-0000-0000-0000-000000000002",
            problem_ids=[1, 2, 3],
        )
        result = compute_match_score(a, b)
        assert result.demographic_score == 40
        assert result.problem_score == 60
        assert result.total_score == 100

    def test_problem_score_1(self):
        """One shared problem → problem_score=20."""
        a = _make_profile(
            user_id="aaaaaaaa-0000-0000-0000-000000000001",
            problem_ids=[1],
        )
        b = _make_profile(
            user_id="bbbbbbbb-0000-0000-0000-000000000002",
            problem_ids=[1, 2],
        )
        result = compute_match_score(a, b)
        assert result.problem_score == 20

    def test_problem_score_2(self):
        """Two shared → problem_score=40."""
        a = _make_profile(
            user_id="aaaaaaaa-0000-0000-0000-000000000001",
            problem_ids=[1, 2],
        )
        b = _make_profile(
            user_id="bbbbbbbb-0000-0000-0000-000000000002",
            problem_ids=[1, 2, 3],
        )
        result = compute_match_score(a, b)
        assert result.problem_score == 40

    def test_problem_score_3(self):
        """Three shared → problem_score=60."""
        a = _make_profile(
            user_id="aaaaaaaa-0000-0000-0000-000000000001",
            problem_ids=[1, 2, 3],
        )
        b = _make_profile(
            user_id="bbbbbbbb-0000-0000-0000-000000000002",
            problem_ids=[1, 2, 3, 4],
        )
        result = compute_match_score(a, b)
        assert result.problem_score == 60

    def test_problem_score_capped(self):
        """Four shared → problem_score still 60 (capped)."""
        a = _make_profile(
            user_id="aaaaaaaa-0000-0000-0000-000000000001",
            problem_ids=[1, 2, 3, 4],
        )
        b = _make_profile(
            user_id="bbbbbbbb-0000-0000-0000-000000000002",
            problem_ids=[1, 2, 3, 4],
        )
        result = compute_match_score(a, b)
        assert result.problem_score == 60

    def test_locale_match(self):
        """Same locale → demo includes 15pts."""
        a = _make_profile(
            user_id="aaaaaaaa-0000-0000-0000-000000000001",
            locale_type="SUBURBAN",
            enrollment=1000,
            frl_pct=50.0,
            ell_pct=50.0,
        )
        b = _make_profile(
            user_id="bbbbbbbb-0000-0000-0000-000000000002",
            locale_type="SUBURBAN",
            enrollment=50000,
            frl_pct=90.0,
            ell_pct=90.0,
        )
        result = compute_match_score(a, b)
        assert result.demographic_score >= 15

    def test_locale_mismatch(self):
        """Different locale → 15pts excluded."""
        a = _make_profile(
            user_id="aaaaaaaa-0000-0000-0000-000000000001",
            locale_type="URBAN",
            enrollment=1000,
            frl_pct=50.0,
            ell_pct=50.0,
        )
        b = _make_profile(
            user_id="bbbbbbbb-0000-0000-0000-000000000002",
            locale_type="RURAL",
            enrollment=50000,
            frl_pct=90.0,
            ell_pct=90.0,
        )
        result = compute_match_score(a, b)
        assert result.demographic_score == 0

    def test_band_small_match(self):
        """Both enrollment < 2500 → demo includes 10pts."""
        a = _make_profile(
            user_id="aaaaaaaa-0000-0000-0000-000000000001",
            locale_type="RURAL",
            enrollment=500,
            frl_pct=90.0,
            ell_pct=90.0,
        )
        b = _make_profile(
            user_id="bbbbbbbb-0000-0000-0000-000000000002",
            locale_type="URBAN",
            enrollment=2000,
            frl_pct=50.0,
            ell_pct=50.0,
        )
        result = compute_match_score(a, b)
        # Different locale (0) + same band (10) + frl diff 40 (0) + ell diff 40 (0) = 10
        assert result.demographic_score == 10

    def test_band_med_small_match(self):
        """Both 2500-7499 → 10pts."""
        a = _make_profile(
            user_id="aaaaaaaa-0000-0000-0000-000000000001",
            locale_type="RURAL",
            enrollment=3000,
            frl_pct=90.0,
            ell_pct=90.0,
        )
        b = _make_profile(
            user_id="bbbbbbbb-0000-0000-0000-000000000002",
            locale_type="URBAN",
            enrollment=7000,
            frl_pct=50.0,
            ell_pct=50.0,
        )
        result = compute_match_score(a, b)
        assert result.demographic_score == 10

    def test_band_medium_match(self):
        """Both 7500-14999 → 10pts."""
        a = _make_profile(
            user_id="aaaaaaaa-0000-0000-0000-000000000001",
            locale_type="RURAL",
            enrollment=8000,
            frl_pct=90.0,
            ell_pct=90.0,
        )
        b = _make_profile(
            user_id="bbbbbbbb-0000-0000-0000-000000000002",
            locale_type="URBAN",
            enrollment=14000,
            frl_pct=50.0,
            ell_pct=50.0,
        )
        result = compute_match_score(a, b)
        assert result.demographic_score == 10

    def test_band_large_match(self):
        """Both 15000-39999 → 10pts."""
        a = _make_profile(
            user_id="aaaaaaaa-0000-0000-0000-000000000001",
            locale_type="RURAL",
            enrollment=20000,
            frl_pct=90.0,
            ell_pct=90.0,
        )
        b = _make_profile(
            user_id="bbbbbbbb-0000-0000-0000-000000000002",
            locale_type="URBAN",
            enrollment=35000,
            frl_pct=50.0,
            ell_pct=50.0,
        )
        result = compute_match_score(a, b)
        assert result.demographic_score == 10

    def test_band_very_large_match(self):
        """Both >= 40000 → 10pts."""
        a = _make_profile(
            user_id="aaaaaaaa-0000-0000-0000-000000000001",
            locale_type="RURAL",
            enrollment=50000,
            frl_pct=90.0,
            ell_pct=90.0,
        )
        b = _make_profile(
            user_id="bbbbbbbb-0000-0000-0000-000000000002",
            locale_type="URBAN",
            enrollment=500000,
            frl_pct=50.0,
            ell_pct=50.0,
        )
        result = compute_match_score(a, b)
        assert result.demographic_score == 10

    def test_band_mismatch(self):
        """1000 vs 10000 → 10pts excluded."""
        a = _make_profile(
            user_id="aaaaaaaa-0000-0000-0000-000000000001",
            locale_type="URBAN",
            enrollment=1000,
            frl_pct=30.0,
            ell_pct=10.0,
        )
        b = _make_profile(
            user_id="bbbbbbbb-0000-0000-0000-000000000002",
            locale_type="URBAN",
            enrollment=10000,
            frl_pct=30.0,
            ell_pct=10.0,
        )
        result = compute_match_score(a, b)
        # Same locale (15) + diff band (0) + same frl (10) + same ell (5) = 30
        assert result.demographic_score == 30

    def test_frl_within_boundary(self):
        """Diff exactly 15.0 → 10pts included."""
        a = _make_profile(
            user_id="aaaaaaaa-0000-0000-0000-000000000001",
            locale_type="RURAL",
            enrollment=1000,
            frl_pct=30.0,
            ell_pct=50.0,
        )
        b = _make_profile(
            user_id="bbbbbbbb-0000-0000-0000-000000000002",
            locale_type="URBAN",
            enrollment=50000,
            frl_pct=45.0,
            ell_pct=90.0,
        )
        result = compute_match_score(a, b)
        # diff locale (0) + diff band (0) + frl diff 15 (10) + ell diff 40 (0) = 10
        assert result.demographic_score == 10

    def test_frl_outside_boundary(self):
        """Diff 15.1 → 10pts excluded."""
        a = _make_profile(
            user_id="aaaaaaaa-0000-0000-0000-000000000001",
            locale_type="RURAL",
            enrollment=1000,
            frl_pct=30.0,
            ell_pct=50.0,
        )
        b = _make_profile(
            user_id="bbbbbbbb-0000-0000-0000-000000000002",
            locale_type="URBAN",
            enrollment=50000,
            frl_pct=45.1,
            ell_pct=90.0,
        )
        result = compute_match_score(a, b)
        assert result.demographic_score == 0

    def test_ell_within_boundary(self):
        """Diff exactly 10.0 → 5pts included."""
        a = _make_profile(
            user_id="aaaaaaaa-0000-0000-0000-000000000001",
            locale_type="RURAL",
            enrollment=1000,
            frl_pct=90.0,
            ell_pct=20.0,
        )
        b = _make_profile(
            user_id="bbbbbbbb-0000-0000-0000-000000000002",
            locale_type="URBAN",
            enrollment=50000,
            frl_pct=50.0,
            ell_pct=30.0,
        )
        result = compute_match_score(a, b)
        # diff locale (0) + diff band (0) + frl diff 40 (0) + ell diff 10 (5) = 5
        assert result.demographic_score == 5

    def test_ell_outside_boundary(self):
        """Diff 10.1 → 5pts excluded."""
        a = _make_profile(
            user_id="aaaaaaaa-0000-0000-0000-000000000001",
            locale_type="RURAL",
            enrollment=1000,
            frl_pct=90.0,
            ell_pct=20.0,
        )
        b = _make_profile(
            user_id="bbbbbbbb-0000-0000-0000-000000000002",
            locale_type="URBAN",
            enrollment=50000,
            frl_pct=50.0,
            ell_pct=30.1,
        )
        result = compute_match_score(a, b)
        assert result.demographic_score == 0

    def test_uuid_ordering_enforced(self):
        """Input with higher UUID as first arg → result.user_a_id is the lower."""
        a = _make_profile(user_id="zzzzzzzz-0000-0000-0000-000000000001")
        b = _make_profile(user_id="aaaaaaaa-0000-0000-0000-000000000002")
        result = compute_match_score(a, b)
        assert result.user_a_id == "aaaaaaaa-0000-0000-0000-000000000002"
        assert result.user_b_id == "zzzzzzzz-0000-0000-0000-000000000001"

    def test_negative_enrollment_band(self):
        """Negative enrollment falls outside all bands → bands don't match."""
        a = _make_profile(
            user_id="aaaaaaaa-0000-0000-0000-000000000001",
            locale_type="URBAN",
            enrollment=-1,
            frl_pct=30.0,
            ell_pct=10.0,
        )
        b = _make_profile(
            user_id="bbbbbbbb-0000-0000-0000-000000000002",
            locale_type="URBAN",
            enrollment=10000,
            frl_pct=30.0,
            ell_pct=10.0,
        )
        result = compute_match_score(a, b)
        # Same locale (15) + diff band (0) + same frl (10) + same ell (5) = 30
        assert result.demographic_score == 30

    def test_all_zeros(self):
        """Different everything, no shared problems → total=0."""
        a = _make_profile(
            user_id="aaaaaaaa-0000-0000-0000-000000000001",
            locale_type="URBAN",
            enrollment=500,
            frl_pct=10.0,
            ell_pct=5.0,
            problem_ids=[1, 2],
        )
        b = _make_profile(
            user_id="bbbbbbbb-0000-0000-0000-000000000002",
            locale_type="RURAL",
            enrollment=50000,
            frl_pct=80.0,
            ell_pct=60.0,
            problem_ids=[3, 4],
        )
        result = compute_match_score(a, b)
        assert result.demographic_score == 0
        assert result.problem_score == 0
        assert result.total_score == 0
