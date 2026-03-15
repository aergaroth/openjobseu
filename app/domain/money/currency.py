from typing import Final

# Mapping of text markers to ISO 4217 currency codes.
# Keys are lowercased. Leading spaces are used to avoid partial word matches
# (e.g. preventing "eur" from matching inside "entrepreneur").
CURRENCY_MARKERS: Final[dict[str, str]] = {
    "€": "EUR",
    "eur": "EUR",
    "euro": "EUR",
    "$": "USD",
    "usd": "USD",
    "dollar": "USD",
    "£": "GBP",
    "gbp": "GBP",
    "pound": "GBP",
    "pln": "PLN",
    "złoty": "PLN",
    "zloty": "PLN",
    "zł": "PLN",
    "chf": "CHF",
    "franc": "CHF",
    "sek": "SEK",
    "nok": "NOK",
    "dkk": "DKK",
    "czk": "CZK",
    "huf": "HUF",
    "ron": "RON",
    "bgn": "BGN",
}

EXCHANGE_RATES = {
    "EUR": 1.0,
    "USD": 0.92,
    "GBP": 1.17,
    "PLN": 0.23,
    "CHF": 1.03,
    "SEK": 0.09,
    "NOK": 0.09,
    "DKK": 0.13,
    "CZK": 0.04,
    "HUF": 0.0025,
    "RON": 0.20,
    "BGN": 0.51,
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

def normalize_to_eur(amount: float, currency: str | None) -> float | None:
    """
    Converts an amount to EUR using predefined exchange rates. Returns a float.
    """
    if not amount or not currency:
        return None
    
    rate = EXCHANGE_RATES.get(currency.upper())
    if not rate:
        return None
    
    return amount * rate
