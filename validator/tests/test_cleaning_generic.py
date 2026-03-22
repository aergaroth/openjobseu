import pytest
from app.utils.cleaning import clean_description


def test_generic_source_keeps_spam_phrase():
    raw = "Valid content.\n\nPlease mention the word TEST"

    cleaned = clean_description(raw, source="greenhouse:acme")

    # spam phrase should NOT be removed for generic ATS sources
    assert "Please mention the word" in cleaned


def test_generic_html_cleanup():
    raw = "Hello<br/><b>World</b>"

    cleaned = clean_description(raw, source="greenhouse:acme")

    assert "<" not in cleaned
    assert "**World**" in cleaned


@pytest.mark.parametrize(
    "raw_html, expected",
    [
        ("Start<p>&nbsp;</p>End", "StartEnd"),
        ("Start<div><br></div>End", "StartEnd"),
        ("Start<p>   </p>End", "StartEnd"),
        ("Start<div><p></p></div>End", "StartEnd"),
        (
            "Start<p class='spacer'>\u00a0</p>End",
            "StartEnd",
        ),  # Tag z klasą i twardą spacją unicode
        ("Start<div>  <br/>  </div>End", "StartEnd"),  # Spacje wokół br
        ("Start<p>\n \n</p>End", "StartEnd"),  # Znaki nowej linii
        ("Start<span class='empty'></span>End", "StartEnd"),  # Pusty span
    ],
)
def test_generic_html_cleanup_removes_empty_tags(raw_html, expected):
    assert clean_description(raw_html, source="greenhouse:acme") == expected


def test_generic_html_cleanup_formats_lists():
    raw = "Requirements:<ul><li>Python</li><li class='item'>SQL</li></ul>"

    cleaned = clean_description(raw, source="greenhouse:acme")

    assert "- Python" in cleaned
    assert "- SQL" in cleaned


def test_generic_html_cleanup_formats_headings():
    raw = "<h1>Main Title</h1><p>Intro</p><h2 class='sub'>Sub Title</h2><p>Details</p>"

    cleaned = clean_description(raw, source="greenhouse:acme")

    assert "# Main Title" in cleaned
    assert "## Sub Title" in cleaned


def test_generic_html_cleanup_formats_links():
    raw = 'Please <a class="btn" href="https://example.com/apply">apply here</a>.'

    cleaned = clean_description(raw, source="greenhouse:acme")

    assert "[apply here](https://example.com/apply)" in cleaned


def test_generic_html_cleanup_formats_italics():
    raw = "<p>This is <i>italic</i>, <em>emphasized</em>, and <u>underlined</u>.</p>"

    cleaned = clean_description(raw, source="greenhouse:acme")

    assert "_italic_" in cleaned
    assert "_emphasized_" in cleaned
    assert "_underlined_" in cleaned


def test_generic_html_cleanup_formats_blockquotes():
    raw = "As our CEO says: <blockquote class='quote'>We are remote first!</blockquote>"

    cleaned = clean_description(raw, source="greenhouse:acme")

    assert "> We are remote first!" in cleaned


def test_generic_html_cleanup_removes_scripts_and_styles():
    raw = "Hello<script>alert('spam');</script>World<style>body {color: red;}</style>!"

    cleaned = clean_description(raw, source="greenhouse:acme")

    assert cleaned == "HelloWorld!"
