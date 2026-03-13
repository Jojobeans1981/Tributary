"""
Pure Python scoring engine — ZERO Django imports.
Computes match scores between two user profiles based on
demographics (0-40) and shared problem statements (0-60).
"""
from dataclasses import dataclass
from typing import List


@dataclass
class DistrictProfile:
    locale_type: str  # "URBAN" | "SUBURBAN" | "RURAL" | "TOWN"
    enrollment: int
    frl_pct: float
    ell_pct: float


@dataclass
class UserMatchProfile:
    user_id: str  # UUID as string
    district: DistrictProfile
    problem_ids: List[int]


@dataclass
class MatchScoreResult:
    user_a_id: str
    user_b_id: str
    demographic_score: int
    problem_score: int
    total_score: int
    shared_problem_ids: List[int]


ENROLLMENT_BANDS = [
    (0, 2499),
    (2500, 7499),
    (7500, 14999),
    (15000, 39999),
    (40000, 9_999_999),
]


def _enrollment_band(n: int) -> int:
    for i, (lo, hi) in enumerate(ENROLLMENT_BANDS):
        if lo <= n <= hi:
            return i
    return -1


def compute_match_score(
    a: UserMatchProfile, b: UserMatchProfile
) -> MatchScoreResult:
    shared = list(set(a.problem_ids) & set(b.problem_ids))
    problem_score = min(len(shared) * 20, 60)

    demo = 0
    if a.district.locale_type == b.district.locale_type:
        demo += 15
    if _enrollment_band(a.district.enrollment) == _enrollment_band(
        b.district.enrollment
    ):
        demo += 10
    if abs(a.district.frl_pct - b.district.frl_pct) <= 15:
        demo += 10
    if abs(a.district.ell_pct - b.district.ell_pct) <= 10:
        demo += 5

    if a.user_id > b.user_id:  # ensure lower UUID is always user_a
        a, b = b, a

    return MatchScoreResult(
        user_a_id=a.user_id,
        user_b_id=b.user_id,
        demographic_score=demo,
        problem_score=problem_score,
        total_score=demo + problem_score,
        shared_problem_ids=shared,
    )
