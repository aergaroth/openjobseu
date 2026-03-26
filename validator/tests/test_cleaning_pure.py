from app.domain.jobs.cleaning import (
    _clean_markdown_artifacts,
    clean_html,
    normalize_whitespace,
)


def test_aggressive_whitespace_normalization_stage_4():
    """Tests Stage 4: Aggressive whitespace normalization."""
    raw_text = """First line.\r\n  \nSecond line.\r \n\n\n\nThird line with non-breaking\xa0space."""
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
    raw_text = "The salary is [53.000](http://53.000) per year."
    expected = "The salary is 53.000 per year."
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
