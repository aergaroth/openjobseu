import html
import re


SPAM_PATTERNS = {
    "mention_word": re.compile(
        r"(?i)please mention the word\s+[a-z0-9]+\s+(?:when applying|in your application)[^\n]*\n?"
    ),
    "beta_spam": re.compile(r"(?i)(?:this is a\s+)?beta feature to avoid spam[^\n]*\n?"),
    "rmt_tag": re.compile(r"RMTg[a-zA-Z0-9+/]+={0,2}\s*\n?"),
    "tracking_pixel": re.compile(r"(?i)<img[^>]+src=[\"'][^\"']*tracking[^\"']*[\"'][^>]*>"),
}


def fix_encoding(text: str) -> str:
    if not text:
        return text

    if any(bad in text for bad in ("â", "Ã", "ð")):
        try:
            return text.encode("latin1").decode("utf-8")
        except Exception:
            return text

    return text


def clean_html(text: str) -> str:
    if not text:
        return text

    # Usuwanie tagów <script> i <style> wraz z całą ich zawartością (kod JS/CSS)
    text = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", text, flags=re.IGNORECASE | re.DOTALL)

    # Wycinka "szumu" rekrutacyjnego ATS (np. RODO, EEO, boilerplate o firmie)
    # Klasa "content-conclusion" (Greenhouse) pojawia się na końcu, więc tniemy aż do końca tekstu
    text = re.sub(
        r"<div[^>]*class=[\"'][^\"']*content-conclusion[^\"']*[\"'][^>]*>.*", "", text, flags=re.IGNORECASE | re.DOTALL
    )
    # Klasa "content-intro" (Greenhouse) jest często u góry, wycinamy pierwszego diva
    text = re.sub(
        r"<div[^>]*class=[\"'][^\"']*content-intro[^\"']*[\"'][^>]*>.*?</div\s*>",
        "",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )

    # Usuwanie pustych paragrafów, divów i spanów (w tym zawierających tylko spacje, &nbsp; lub <br>)
    # Puszczamy to dwukrotnie, aby wyłapać zagnieżdżone przypadki
    empty_tag_pattern = r"<(p|div|span)[^>]*>(?:&nbsp;|\u00A0|<br\s*/?>|\s)*</\1>"
    text = re.sub(empty_tag_pattern, "", text, flags=re.IGNORECASE)
    text = re.sub(empty_tag_pattern, "", text, flags=re.IGNORECASE)

    # Formatowanie strukturalne do czystego Markdown-like
    text = re.sub(r"</p\s*>", "\n\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<p[^>]*>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<hr[^>]*>", "\n---\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<h1[^>]*>", "\n# ", text, flags=re.IGNORECASE)
    text = re.sub(r"<h2[^>]*>", "\n## ", text, flags=re.IGNORECASE)
    text = re.sub(r"<h3[^>]*>", "\n### ", text, flags=re.IGNORECASE)
    text = re.sub(r"<h4[^>]*>", "\n#### ", text, flags=re.IGNORECASE)
    text = re.sub(r"<h5[^>]*>", "\n##### ", text, flags=re.IGNORECASE)
    text = re.sub(r"<h6[^>]*>", "\n###### ", text, flags=re.IGNORECASE)
    text = re.sub(r"</h[1-6]\s*>", "\n\n", text, flags=re.IGNORECASE)

    text = re.sub(r"<blockquote[^>]*>", "\n> ", text, flags=re.IGNORECASE)
    text = re.sub(r"</blockquote\s*>", "\n\n", text, flags=re.IGNORECASE)

    text = re.sub(r"<li[^>]*>", "\n- ", text, flags=re.IGNORECASE)
    text = re.sub(r"</li\s*>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"</(ul|ol)\s*>", "\n\n", text, flags=re.IGNORECASE)

    text = re.sub(r"<(b|strong)[^>]*>", "**", text, flags=re.IGNORECASE)
    text = re.sub(r"</(b|strong)\s*>", "**", text, flags=re.IGNORECASE)
    text = re.sub(r"<(i|em|u)[^>]*>", "_", text, flags=re.IGNORECASE)
    text = re.sub(r"</(i|em|u)\s*>", "_", text, flags=re.IGNORECASE)

    # Upraszczanie linków - wyciągamy tylko Anchor Text (usuwamy szum samych URL pod LLM)
    text = re.sub(
        r"<a[^>]*>(.*?)</a>",
        r"\1",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )

    text = re.sub(r"</div\s*>", "\n\n", text, flags=re.IGNORECASE)

    # Ostateczne usunięcie pozostałych tagów HTML (takich jak <span>, <article>, osierocone atrybuty)
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)

    # Wstępna redukcja wielu pustych linii po wyrzucaniu divów
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def normalize_whitespace(text: str) -> str:
    if not text:
        return text

    text = text.replace("\r\n", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
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

    text = fix_encoding(text)
    text = clean_html(text)

    if source == "remoteok":
        for name, pattern in SPAM_PATTERNS.items():
            text = pattern.sub("", text)

    text = normalize_whitespace(text)
    return text
