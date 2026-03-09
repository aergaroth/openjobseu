from typing import Final

# Mapping of text markers to ISO 4217 currency codes.
# Keys are lowercased. Leading spaces are used to avoid partial word matches
# (e.g. preventing "eur" from matching inside "entrepreneur").
CURRENCY_MARKERS: Final[dict[str, str]] = {
    "€": "EUR",
    " eur": "EUR",
    " euro": "EUR",
    "$": "USD",
    " usd": "USD",
    " dollar": "USD",
    "£": "GBP",
    " gbp": "GBP",
    " pound": "GBP",
    " pln": "PLN",
    " zł": "PLN",
    " zloty": "PLN",
    " chf": "CHF",
    " sek": "SEK",
    " nok": "NOK",
    " dkk": "DKK",
    " czk": "CZK",
    " huf": "HUF",
    " ron": "RON",
    " bgn": "BGN",
}


def detect_currency(text: str) -> str | None:
    """
    Detect currency from text using a marker mapping.
    """
    text_lower = text.lower()
    for marker, code in CURRENCY_MARKERS.items():
        if marker in text_lower:
            return code
    return None