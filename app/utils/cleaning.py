import html
import re


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

    text = re.sub(r"</p\s*>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<p\s*>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)
    return text


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
    text = normalize_whitespace(text)
    return text
