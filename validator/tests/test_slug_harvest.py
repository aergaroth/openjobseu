from app.workers.discovery.slug_harvest import (
    _extract_candidates_from_text,
    _score_candidate,
    SlugCandidate,
)


def test_extract_candidates_traffit():
    cands = _extract_candidates_from_text("https://acme-hr.traffit.com/public/job_posts/published", "final_url")
    assert any(c.provider == "traffit" and c.slug == "acme-hr" for c in cands)


def test_extract_candidates_breezy():
    cands = _extract_candidates_from_text("https://my-company.breezy.hr/json", "final_url")
    assert any(c.provider == "breezy" and c.slug == "my-company" for c in cands)


def test_extract_candidates_jobadder():
    cands = _extract_candidates_from_text("https://app.jobadder.com/jobboard/abc-123", "final_url")
    assert any(c.provider == "jobadder" and c.slug == "abc-123" for c in cands)


def test_extract_candidates_teamtailor_subdomain():
    cands = _extract_candidates_from_text("https://acme.teamtailor.com/jobs", "final_url")
    assert any(c.provider == "teamtailor" and c.slug == "acme" for c in cands)


def test_score_requires_final_url_to_hit_threshold():
    c = SlugCandidate(provider="traffit", slug="acme-hr", evidence="html")
    assert _score_candidate(c, occurrences=1, from_final_url=False) < 2
    assert _score_candidate(c, occurrences=2, from_final_url=False) < 2
    assert _score_candidate(c, occurrences=1, from_final_url=True) >= 2

