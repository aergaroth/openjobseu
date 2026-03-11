from app.workers.discovery.careers_crawler import (
    _detect_provider,
    INVALID_SLUG_KEYWORDS,
    _is_valid_slug,
    _detect_provider_with_shallow_crawl,
    _extract_candidate_links,
    MAX_SECONDARY_LINKS,
)


def test_detect_greenhouse_slug():
    assert _detect_provider('https://boards.greenhouse.io/acme-team') == ('greenhouse', 'acme-team')


def test_detect_lever_slug():
    assert _detect_provider('https://jobs.lever.co/acme_inc') == ('lever', 'acme_inc')


def test_detect_workable_slug():
    assert _detect_provider('https://apply.workable.com/acme-io') == ('workable', 'acme-io')


def test_detect_none_when_missing():
    assert _detect_provider('https://example.com') is None


def test_invalid_slug_keywords_discarded():
    slug = f"acme-{next(iter(INVALID_SLUG_KEYWORDS))}"
    assert not _is_valid_slug(slug)


def test_valid_slug_accepted():
    assert _is_valid_slug('acme-team')


def test_slug_too_short_rejected():
    assert not _is_valid_slug('ab')


def test_candidate_links_limited_to_max():
    anchor_html = ''.join(
        f"<a href='/jobs/{i}'>Job {i}</a>" for i in range(MAX_SECONDARY_LINKS + 3)
    )
    links = _extract_candidate_links(anchor_html, 'https://company.com/careers')
    assert len(links) == MAX_SECONDARY_LINKS


def test_shallow_crawl_follows_candidate_links(monkeypatch):
    html = '<a href="/jobs">See jobs</a>'
    def fake_fetch(url: str):
        if url.endswith('/jobs'):
            return ('https://boards.greenhouse.io/acme-team', '<html>')
        return None
    monkeypatch.setattr(
        'app.workers.discovery.careers_crawler._fetch_careers_page',
        fake_fetch,
    )

    result = _detect_provider_with_shallow_crawl(
        'https://company.com/careers',
        html,
    )
    assert result == ('greenhouse', 'acme-team')


def test_shallow_crawl_returns_none_when_candidate_fetch_fails(monkeypatch):
    html = '<a href="/jobs">See jobs</a>'
    monkeypatch.setattr(
        'app.workers.discovery.careers_crawler._fetch_careers_page',
        lambda url: None,
    )

    assert _detect_provider_with_shallow_crawl('https://company.com/careers', html) is None