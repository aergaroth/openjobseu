from app.domain.jobs.cleaning import (
    clean_html,
    clean_description,
    fix_encoding,
    _clean_markdown_artifacts,
)


def test_clean_html_removes_inline_styles_and_spans():
    # Przykład z Elastic (Greenhouse)
    raw_html = '<h3><span style="font-size: 12pt;"><strong>What is The Role:</strong></span></h3>'
    # Oczekujemy czystego Markdowna lub chociaż oczyszczonego tekstu bez spanów
    cleaned = clean_html(raw_html)
    assert "What is The Role:" in cleaned
    assert "<span" not in cleaned
    assert "style=" not in cleaned


def test_clean_html_removes_eeo_conclusion_block():
    # Przykład z Elastic (Greenhouse) - ukryty blok z RODO i EEO
    raw_html = """
    <p>Some useful job description.</p>
    <div class="content-conclusion">
        <h2><strong>Additional Information - We Take Care of Our People</strong></h2>
        <p>As a distributed company, diversity drives our identity...</p>
        <p>Elastic is an equal opportunity employer...</p>
    </div>
    """
    cleaned = clean_html(raw_html)
    assert "Some useful job description." in cleaned
    assert "Additional Information" not in cleaned
    assert "equal opportunity employer" not in cleaned
    assert "content-conclusion" not in cleaned


def test_clean_html_formats_lists_and_removes_complex_classes():
    # Przykład z Doctolib (Greenhouse)
    raw_html = """
    <ul class="s-list-disc s-pb-2 s-pl-6 s-text-foreground dark:s-text-foreground-night s-text-base s-leading-7">
        <li class="s-break-words s-text-foreground dark:s-text-foreground-night s-text-base s-leading-7">
            Design, ship, and operate production-grade agentic systems
        </li>
        <li class="s-break-words s-text-foreground dark:s-text-foreground-night s-text-base s-leading-7">
            Ensure privacy and security by design
        </li>
    </ul>
    """
    cleaned = clean_html(raw_html)

    # Powinny zniknąć klasy, a lista powinna przypominać Markdown lub czysty tekst
    assert "s-list-disc" not in cleaned
    assert "Design, ship, and operate production-grade agentic systems" in cleaned
    assert "Ensure privacy and security by design" in cleaned


def test_clean_html_handles_custom_data_attributes():
    # Przykład z Datadog (Greenhouse)
    raw_html = (
        '<p data-renderer-start-pos="215"><strong data-renderer-mark="true">Equal Opportunity at Datadog:</strong></p>'
    )
    cleaned = clean_html(raw_html)

    assert "Equal Opportunity at Datadog:" in cleaned
    assert "data-renderer" not in cleaned


def test_clean_html_preserves_plain_text():
    # Przykład z Pigment (Lever) - czasem ATSy oddają czysty tekst, funkcja nie może go zepsuć
    raw_text = """
    Join Pigment: The AI Platform Redefining Business Planning
    
    Pigment is the AI-powered business planning and performance management platform built for agility and scale.
    """
    cleaned = clean_html(raw_text)
    assert "Join Pigment: The AI Platform" in cleaned
    assert "built for agility and scale." in cleaned


def test_clean_html_removes_excessive_whitespace():
    # Częsty problem po konwersji list i br tagów
    raw_html = "<p>First line.</p><br><br><br><br><p>Second line.</p>"
    cleaned = clean_html(raw_html)

    # Powinno zredukować wielokrotne entery
    assert "\n\n\n" not in cleaned
    assert "First line." in cleaned
    assert "Second line." in cleaned


def test_clean_html_removes_scripts_and_styles():
    raw_html = "<div>Witaj<script>alert('spam');</script><style>body {color: red;}</style></div>"
    cleaned = clean_html(raw_html)
    assert "Witaj" in cleaned
    assert "alert" not in cleaned
    assert "color: red" not in cleaned


def test_fix_encoding_resolves_mojibake():
    # Błędnie zdekodowany apostrof (Right Single Quotation Mark) jako latin-1: "Weâ\x80\x99re"
    raw_mojibake = "We\u00e2\u0080\u0099re looking for engineers."
    fixed = fix_encoding(raw_mojibake)
    assert fixed == "We’re looking for engineers."


def test_fix_encoding_ignores_valid_utf8_and_emojis():
    # Poprawny tekst w UTF-8 z polskimi znakami i emoji nie może zostać uszkodzony
    valid_text = "Zażółć gęślą jaźń 🚀 😊"
    fixed = fix_encoding(valid_text)
    assert fixed == valid_text


def test_clean_description_removes_remoteok_spam():
    raw_text = """
    <p>We are hiring!</p>
    <p>Please mention the word BANANA when applying to prove you are human.</p>
    <p>This is a beta feature to avoid spam.</p>
    <p>RMTgabc123==</p>
    """
    cleaned = clean_description(raw_text, source="remoteok")
    assert "We are hiring!" in cleaned
    assert "BANANA" not in cleaned
    assert "beta feature" not in cleaned
    assert "RMTgabc" not in cleaned


def test_clean_description_preserves_spam_patterns_for_other_sources():
    # Jeśli source nie jest 'remoteok', filtry na specyficzny spam nie powinny się uruchomić
    raw_text = "<p>Please mention the word BANANA when applying.</p>"
    cleaned = clean_description(raw_text, source="greenhouse")
    assert "BANANA" in cleaned


def test_clean_markdown_artifacts():
    raw_md = """
    # Header
    ** **
    __ __
    [1.2.3](http://1.2.3)
    """
    cleaned = _clean_markdown_artifacts(raw_md)
    assert "** **" not in cleaned
    assert "__ __" not in cleaned
    assert "1.2.3" in cleaned  # Malformed link z ATS został odzyskany do czystego tekstu
    assert "[1.2.3]" not in cleaned
