from app.domain.jobs.cleaning import (
    _clean_markdown_artifacts,
    clean_html,
    normalize_whitespace,
    normalize_remote_scope,
    clean_description,
)


def test_aggressive_whitespace_normalization_stage_4():
    """Tests Stage 4: Aggressive whitespace normalization."""
    raw_text = """First line.
  
Second line.
 


Third line with non-breaking space."""
    expected = "First line.\n\nSecond line.\n\nThird line with non-breaking space."
    cleaned = normalize_whitespace(raw_text)
    assert cleaned == expected


def test_markdown_artifact_cleaning_stage_2():
    """Tests Stage 2: Eliminating various markdown artifacts."""
    raw_text = """
# 
## Some Header

- 
- An item
** **
___

Another item.
"""
    expected = "## Some Header\n\n- An item\n\nAnother item."
    cleaned = _clean_markdown_artifacts(raw_text)
    # Also run whitespace normalization to clean up empty lines left by artifact removal
    cleaned = normalize_whitespace(cleaned)
    assert cleaned == expected


def test_broken_link_fixing_stage_3():
    """Tests Stage 3: Fixing broken numeric links from ATS."""
    raw_text = "The salary is [53.000](http://53.000) per year and secure link [1.2.3](https://1.2.3)."
    expected = "The salary is 53.000 per year and secure link 1.2.3."
    cleaned = _clean_markdown_artifacts(raw_text)
    assert cleaned == expected


def test_boilerplate_removal_stage_1():
    """Tests Stage 1: Semantic removal of boilerplate text."""
    raw_text = """
This is the main job description.

We hire for skills and potential, and we are an equal opportunity employer.

Some more text here.

Please review our Candidate Privacy Notice for more details.
"""
    expected = "This is the main job description.\n\nSome more text here."
    # This cleaning happens inside clean_html, which we test here as a whole.
    cleaned = clean_html(raw_text)
    cleaned = normalize_whitespace(cleaned)  # Normalize to ensure consistent comparison
    assert cleaned == expected


def test_normalize_remote_scope():
    assert normalize_remote_scope("Remote - Europe") == "europe"
    assert normalize_remote_scope("remote europe") == "europe"
    assert normalize_remote_scope("EU Remote") == "europe"
    assert normalize_remote_scope("Remote (EU)") == "europe"
    assert normalize_remote_scope("Remote Worldwide") == "worldwide"
    assert normalize_remote_scope("  remote - europe  ") == "europe"
    assert normalize_remote_scope("some other value") == "some other value"
    assert normalize_remote_scope(None) == ""
    assert normalize_remote_scope("") == ""


def test_clean_description_removes_remoteok_spam():
    spam_text = "please mention the word foobar when applying. this is a beta feature to avoid spam"
    text = f"Job description.\n{spam_text}\nMore description."
    cleaned = clean_description(text, source="remoteok")
    assert "Job description." in cleaned
    assert "More description." in cleaned
    assert spam_text not in cleaned


def test_clean_description_does_not_remove_spam_for_other_sources():
    spam_text = "please mention the word foobar when applying. this is a beta feature to avoid spam"
    text = f"Job description.\n{spam_text}\nMore description."
    cleaned = clean_description(text, source="other_source")
    assert spam_text in cleaned


def test_clean_description_fallback_on_error(monkeypatch):
    """Sprawdza, czy moduł wpada w miękki fallback na wypadek wyjątku."""

    def mock_clean_html(*args, **kwargs):
        raise ValueError("Simulated pipeline error")

    monkeypatch.setattr("app.domain.jobs.cleaning.clean_html", mock_clean_html)

    raw_text = "<p>Some <b>job</b></p>"
    result = clean_description(raw_text, "test_source")
    assert result == "Some job"
