from app.workers.normalization.cleaning import clean_description


def test_non_remoteok_keeps_spam_phrase():
    raw = "Valid content.\n\nPlease mention the word TEST"

    cleaned = clean_description(raw, source="remotive")

    # spam phrase should NOT be removed for non-remoteok
    assert "Please mention the word" in cleaned


def test_generic_html_cleanup():
    raw = "Hello<br/><b>World</b>"

    cleaned = clean_description(raw, source="remotive")

    assert "<" not in cleaned
    assert "World" in cleaned
