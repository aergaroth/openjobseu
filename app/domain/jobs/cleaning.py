import html
import re
import logging
import charset_normalizer

logger = logging.getLogger(__name__)


SPAM_PATTERNS = {
    "mention_word": re.compile(
        r"(?i)please mention the word\s+[a-z0-9]+\s+(?:when applying|in your application)[^\n]*\n?"
    ),
    "beta_spam": re.compile(r"(?i)(?:this is a\s+)?beta feature to avoid spam[^\n]*\n?"),
    "rmt_tag": re.compile(r"(?i)rmtg[-a-z0-9+/]+={0,2}\s*\n?"),
    "tracking_pixel": re.compile(r"(?i)<img[^>]+src=[\"'][^\"']*tracking[^\"']*[\"'][^>]*>"),
}

BOILERPLATE_PATTERNS = {
    "eeo_statement": re.compile(
        r"(?i)(?:\n\n|^)[^\n]*(?:is proud to be an equal opportunity employer|is an equal opportunity employer|is committed to working with the broadest talent pool|We hire for skills and potential)[\s\S]*?(?=\n\s*\n|$)"
    ),
    "privacy_notice": re.compile(
        r"(?i)(?:\n\n|^)[^\n]*(?:Please review our Candidate Privacy Notice|For information about our privacy practices, please visit)[\s\S]*?(?=\n\s*\n|$)"
    ),
}

HTML_CLEANING_PATTERNS = [
    (re.compile(r"<(script|style)[^>]*>.*?</\1>", flags=re.IGNORECASE | re.DOTALL), ""),
    (re.compile(r"<div[^>]*class=[\"'][^\"']*content-conclusion[^\"']*[\"'][^>]*>.*", flags=re.IGNORECASE | re.DOTALL), ""),
    (re.compile(r"<div[^>]*class=[\"'][^\"']*content-intro[^\"']*[\"'][^>]*>.*?</div\s*>", flags=re.IGNORECASE | re.DOTALL), ""),
]

# Wymaga przechwytywania (p|div|span), żeby zamknąć poprawny tag w </\1>
EMPTY_TAG_PATTERN = re.compile(r"<(p|div|span)[^>]*>(?:&nbsp;|\u00A0|<br\s*/?>|\s)*</\1>", flags=re.IGNORECASE)

HTML_FORMATTING_PATTERNS = [
    (re.compile(r"</p\s*>", flags=re.IGNORECASE), "\n\n"),
    (re.compile(r"<p[^>]*>", flags=re.IGNORECASE), ""),
    (re.compile(r"<br\s*/?>", flags=re.IGNORECASE), "\n"),
    (re.compile(r"<hr[^>]*>", flags=re.IGNORECASE), "\n---\n"),
    (re.compile(r"<h1[^>]*>", flags=re.IGNORECASE), "\n# "),
    (re.compile(r"<h2[^>]*>", flags=re.IGNORECASE), "\n## "),
    (re.compile(r"<h3[^>]*>", flags=re.IGNORECASE), "\n### "),
    (re.compile(r"<h4[^>]*>", flags=re.IGNORECASE), "\n#### "),
    (re.compile(r"<h5[^>]*>", flags=re.IGNORECASE), "\n##### "),
    (re.compile(r"<h6[^>]*>", flags=re.IGNORECASE), "\n###### "),
    (re.compile(r"</h[1-6]\s*>", flags=re.IGNORECASE), "\n\n"),
    (re.compile(r"<blockquote[^>]*>", flags=re.IGNORECASE), "\n> "),
    (re.compile(r"</blockquote\s*>", flags=re.IGNORECASE), "\n\n"),
    (re.compile(r"<li[^>]*>", flags=re.IGNORECASE), "\n- "),
    (re.compile(r"</li\s*>", flags=re.IGNORECASE), ""),
    (re.compile(r"</(?:ul|ol)\s*>", flags=re.IGNORECASE), "\n\n"),
    (re.compile(r"<(?:b|strong)[^>]*>", flags=re.IGNORECASE), "**"),
    (re.compile(r"</(?:b|strong)\s*>", flags=re.IGNORECASE), "**"),
    (re.compile(r"<(?:i|em|u)[^>]*>", flags=re.IGNORECASE), "_"),
    (re.compile(r"</(?:i|em|u)\s*>", flags=re.IGNORECASE), "_"),
    (re.compile(r"<a[^>]*>(.*?)</a>", flags=re.IGNORECASE | re.DOTALL), r"\1"),
    (re.compile(r"</div\s*>", flags=re.IGNORECASE), "\n\n"),
]

REMAINING_HTML_TAGS = re.compile(r"<[^>]+>")

# Używany w clean_html (po wyrzuceniu divów) i normalize_whitespace (finalna normalizacja).
COLLAPSE_NEWLINES = re.compile(r"\n{3,}")

WHITESPACE_TRIM_END_LINES = re.compile(r"[ \t]+\n")
WHITESPACE_COLLAPSE_SPACES = re.compile(r"[ \t]+")

MD_MALFORMED_LINKS = re.compile(r"\[([0-9\.]+)\]\(https?://[0-9\.]+\)")
MD_EMPTY_BOLD = re.compile(r"\*+\s*\*+")
MD_EMPTY_ITALIC = re.compile(r"_+\s*_+")
# Usuwa linie złożone wyłącznie z symboli markdown (puste nagłówki, listy, kursywa),
# ale zachowuje separatory poziome `---` i `***` wstawione przez konwersję <hr>.
MD_EMPTY_LINES = re.compile(r"^\s*(?!-{3,}$|\*{3,}$)([#*_-]+|>{1,})\s*$", flags=re.MULTILINE)
MD_LEFTOVER_MARKERS = re.compile(r"^\s*(\*\*|__)\s*$", flags=re.MULTILINE)

# Znaki charakterystyczne dla mojibake UTF-8 zdekodowanego jako latin1.
# Sprawdzamy tylko znaki spoza ASCII, żeby uniknąć kosztownej ścieżki dla czystego tekstu.
_MOJIBAKE_CHARS = frozenset("â\x80\x99Ã\x82ð\x9f")


def fix_encoding(text: str) -> str:
    if not text:
        return text

    # Szybki pre-check: jeśli tekst jest czystym ASCII lub nie zawiera podejrzanych
    # sekwencji, pomijamy kosztowne encode/decode przez charset_normalizer.
    if text.isascii() or not any(c in text for c in _MOJIBAKE_CHARS):
        return text

    try:
        # Mojibake składa się ze znaków jednobajtowych.
        # Rzutujemy tekst na latin1, by uzyskać pierwotne bajty przed błędnym dekodowaniem.
        raw_bytes = text.encode("latin1")

        # charset_normalizer bada bajty i zwraca najlepsze dopasowanie (najczęściej utf-8).
        match = charset_normalizer.from_bytes(raw_bytes).best()
        if match is not None:
            decoded = str(match)
            # Podmieniamy tylko gdy wynik faktycznie różni się od wejścia —
            # zapobiega uszkodzeniu poprawnych tekstów przez błędne zgadywanie kodowania.
            if decoded != text:
                return decoded
    except UnicodeEncodeError:
        # Tekst zawiera znaki spoza zakresu latin1 (np. emoji) — na pewno nie mojibake.
        pass
    except Exception as e:
        logger.debug("Failed to fix encoding with charset_normalizer: %s", e)

    return text


def clean_html(text: str) -> str:
    if not text:
        return text

    for pattern, repl in HTML_CLEANING_PATTERNS:
        text = pattern.sub(repl, text)

    # Usuwanie pustych paragrafów, divów i spanów (podwójny przebieg na zagnieżdżenia)
    text = EMPTY_TAG_PATTERN.sub("", text)
    text = EMPTY_TAG_PATTERN.sub("", text)

    for pattern, repl in HTML_FORMATTING_PATTERNS:
        text = pattern.sub(repl, text)

    # Ostateczne usunięcie pozostałych tagów HTML (takich jak <span>, <article>, osierocone atrybuty)
    text = REMAINING_HTML_TAGS.sub("", text)
    text = html.unescape(text)

    # Semantyczna wycinka boilerplate'u po konwersji na tekst
    for _, pattern in BOILERPLATE_PATTERNS.items():
        text = pattern.sub("", text)

    # Wstępna redukcja wielu pustych linii po wyrzucaniu divów
    text = COLLAPSE_NEWLINES.sub("\n\n", text)

    return text.strip()


def normalize_whitespace(text: str) -> str:
    if not text:
        return text

    # Standardize all forms of newlines and non-breaking spaces
    text = text.replace("\r\n", "\n")
    text = text.replace("\r", "\n")
    text = text.replace("\xa0", " ")

    # Trim whitespace at the end of lines
    text = WHITESPACE_TRIM_END_LINES.sub("\n", text)

    # Collapse multiple spaces/tabs into a single space
    text = WHITESPACE_COLLAPSE_SPACES.sub(" ", text)

    # Collapse multiple newlines into a maximum of two
    text = COLLAPSE_NEWLINES.sub("\n\n", text)

    return text.strip()


def normalize_remote_scope(value: str | None) -> str:
    """
    Normalize remote/location strings across ATS providers.
    """
    if not value:
        return ""

    value = value.lower().strip()

    replacements = {
        "remote - europe": "europe",
        "remote europe": "europe",
        "eu remote": "europe",
        "remote eu": "europe",
        "remote (eu)": "europe",
        "remote worldwide": "worldwide",
    }

    return replacements.get(value, value)


def clean_description(text: str, source: str) -> str:
    if not text:
        return text

    try:
        logger.debug("Starting cleaning for source '%s' - original length: %d", source, len(text))

        # First pass: basic encoding and HTML cleaning
        text = fix_encoding(text)
        text = clean_html(text)
        text = _clean_markdown_artifacts(text)

        logger.debug("After first pass - length: %d", len(text))

        # For remoteok source, remove spam patterns BEFORE whitespace normalization
        if source == "remoteok":
            for _, pattern in SPAM_PATTERNS.items():
                text = pattern.sub("", text)

        # Validate that no HTML tags remain
        if REMAINING_HTML_TAGS.search(text):
            logger.warning("HTML tags still present after initial cleaning for source '%s'", source)
            text = REMAINING_HTML_TAGS.sub("", text)
            text = html.unescape(text)

        logger.debug("After aggressive cleaning - length: %d", len(text))

        # Remove any remaining whitespace artifacts
        text = normalize_whitespace(text)

        logger.debug("Cleaning completed successfully for source '%s'", source)
        return text.strip()

    except Exception:
        logger.exception("Cleaning failed for source '%s'", source)
        # Fallback: remove all HTML tags and return basic cleaned text
        text = REMAINING_HTML_TAGS.sub("", text)
        text = html.unescape(text)
        text = normalize_whitespace(text)
        logger.debug("Fallback cleaning completed for source '%s'", source)
        return text.strip()


def _clean_markdown_artifacts(text: str) -> str:
    if not text:
        return text

    # Fix for ATS converting numbers with dots into malformed links
    text = MD_MALFORMED_LINKS.sub(r"\1", text)

    # Remove empty markdown formatting like ****, __, ** **, etc.
    # by replacing them with a single space to avoid joining words.
    text = MD_EMPTY_BOLD.sub(" ", text)
    text = MD_EMPTY_ITALIC.sub(" ", text)

    # Remove empty lines that are just markdown symbols (e.g., "- ", "# ", "_")
    # This handles empty list items, headers, and standalone formatting characters.
    text = MD_EMPTY_LINES.sub("", text)

    # Clean up leftover empty bold/italic markers, often on their own lines
    text = MD_LEFTOVER_MARKERS.sub("", text)

    return text
