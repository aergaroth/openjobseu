import re
import html


SPAM_MARKER = "Please mention the word"


def fix_encoding(text: str) -> str:
    """
    Attempts to fix common UTF-8 mis-decoded as latin1 issues.
    Safe fallback to original text.
    """
    if not text:
        return text

    # Heuristic: only attempt if suspicious sequences present
    if any(bad in text for bad in ("â", "Ã", "ð")):
        try:
            return text.encode("latin1").decode("utf-8")
        except Exception:
            return text

    return text


def remove_remoteok_spam(text: str, source: str) -> str:
    """
    Removes RemoteOK anti-bot footer.
    Safe deterministic rule: remove everything from SPAM_MARKER onward.
    """
    if source != "remoteok":
        return text

    if SPAM_MARKER in text:
        return text.split(SPAM_MARKER)[0]

    return text


def clean_html(text: str) -> str:
    if not text:
        return text

    # Paragraph tags → newline
    text = re.sub(r"</p\s*>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<p\s*>", "\n", text, flags=re.IGNORECASE)

    # <br> variants → newline
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)

    # Remove remaining tags
    text = re.sub(r"<[^>]+>", "", text)

    # Unescape HTML entities
    text = html.unescape(text)

    return text



def normalize_whitespace(text: str) -> str:
    """
    Normalizes spacing and newlines.
    """
    if not text:
        return text

    text = text.replace("\r\n", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def clean_description(text: str, source: str) -> str:
    """
    Main cleaning entrypoint.
    Order matters.
    """
    if not text:
        return text

    text = fix_encoding(text)
    text = remove_remoteok_spam(text, source)
    text = clean_html(text)
    text = normalize_whitespace(text)

    return text
