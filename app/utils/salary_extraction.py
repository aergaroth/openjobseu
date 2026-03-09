import re
import logging
from app.domain.classification.currency_mapper import detect_currency

logger = logging.getLogger(__name__)

# --- CONFIGURATION ---

SALARY_KEYWORDS = [
    "salary",
    "compensation",
    "pay",
    "base",
    "earning",
    "earnings",
    "ote",
    "on target earnings",
    "rate",
    "per year",
    "per month",
    "per hour",
    "remuneration",
    "package",
]

NEGATIVE_CONTEXT = [
    "years",
    "year experience",
    "years experience",
    "customers",
    "users",
    "downloads",
    "companies",
    "employees",
    "team",
    "offices",
    "founded",
    "established",
]

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

def detect_period(text: str) -> str:
    if "hour" in text:
        return "hour"
    if "month" in text:
        return "month"
    if "day" in text:
        return "day"
    return "year"

def is_valid_salary_context(text: str, start: int, end: int) -> bool:
    """
    Check surrounding text for positive/negative signals.
    """
    # Context window: 40 chars before and after
    window_start = max(0, start - 40)
    window_end = min(len(text), end + 40)
    window = text[window_start:window_end]

    # 1. Reject negative context immediately
    for word in NEGATIVE_CONTEXT:
        if word in window:
            return False

    # 2. Accept if positive keyword is present
    for word in SALARY_KEYWORDS:
        if word in window:
            return True

    # 3. Default: Accept (neutral), but relying on strict regex patterns
    return True

def normalize_to_eur(amount: int, currency: str | None) -> int | None:
    if not amount or not currency:
        return None
    
    rate = EXCHANGE_RATES.get(currency.upper())
    if not rate:
        return None
    
    return int(amount * rate)

def is_reasonable_salary(min_val: int, max_val: int, period: str) -> bool:
    """
    Sanity check for salary ranges. Converts to yearly equivalent for validation.
    """
    # 1. Ratio check: max shouldn't be more than 5x min (e.g. 10k-100k is suspicious)
    if max_val > min_val * 5:
        return False

    # Normalize to yearly for magnitude check
    multiplier = 1
    if period == "month":
        multiplier = 12
    elif period == "hour":
        multiplier = 2000  # approx working hours
    elif period == "day":
        multiplier = 250

    yearly_min = min_val * multiplier
    yearly_max = max_val * multiplier

    # Reasonable yearly range: 15k - 500k EUR/USD equivalent
    return yearly_min >= 15000 and yearly_max <= 500000

def extract_salary(description: str) -> dict | None:
    if not description:
        return None

    text = description.lower()
    text = text.replace(",", "")
    text = text.replace(".", "")

    currency = detect_currency(text)
    period = detect_period(text)

    patterns = [
        (r"(\d{2,3})\s?k\s?[-–]\s?(\d{2,3})\s?k", 1000),  # RANGE WITH K
        (r"[€$£]?\s?(\d{2,3})k\s?[-–]\s?[€$£]?\s?(\d{2,3})k", 1000),  # RANGE WITH CURRENCY
        (r"(\d{4,6})\s?[-–]\s?(\d{4,6})", 1),  # RANGE FULL
    ]

    for pattern_str, multiplier in patterns:
        # Use finditer to skip invalid matches (e.g. years) and find real salary later in text
        for m in re.finditer(pattern_str, text):
            if not is_valid_salary_context(text, m.start(), m.end()):
                logger.debug(
                    "salary rejected due to context",
                    extra={"match": m.group(0), "context": text[max(0, m.start()-20):m.end()+20]}
                )
                continue

            min_val = int(m.group(1)) * multiplier
            max_val = int(m.group(2)) * multiplier

            if not is_reasonable_salary(min_val, max_val, period):
                continue

            # Success
            return {
                "salary_min": min_val,
                "salary_max": max_val,
                "salary_currency": currency,
                "salary_period": period,
                "salary_source": "regex_v3",
                # Normalized fields for analytics
                "salary_min_eur": normalize_to_eur(min_val, currency),
                "salary_max_eur": normalize_to_eur(max_val, currency),
            }

    # SINGLE VALUE
    # Use finditer here as well
    for m in re.finditer(r"[€$£]?\s?(\d{2,3})k\b", text):
        if not is_valid_salary_context(text, m.start(), m.end()):
            continue

        value = int(m.group(1)) * 1000
        
        if not is_reasonable_salary(value, value, period):
            continue

        return {
            "salary_min": value,
            "salary_max": value,
            "salary_currency": currency,
            "salary_period": period,
            "salary_source": "regex_v3",
            "salary_min_eur": normalize_to_eur(value, currency),
            "salary_max_eur": normalize_to_eur(value, currency),
        }

    # HOURLY RATE
    for m in re.finditer(r"(\d{2,3})\s?(usd|eur|\$|€)?\s?/?\s?hour", text):
        if not is_valid_salary_context(text, m.start(), m.end()):
            continue

        value = int(m.group(1))
        
        # Detect currency locally if not global, or fallback
        local_currency = currency
        if not local_currency:
            local_currency = detect_currency(m.group(0))

        # Hourly specific sanity check (10 - 500)
        if value < 10 or value > 500:
            continue

        return {
            "salary_min": value,
            "salary_max": value,
            "salary_currency": local_currency,
            "salary_period": "hour",
            "salary_source": "regex_v3",
            "salary_min_eur": normalize_to_eur(value, local_currency),
            "salary_max_eur": normalize_to_eur(value, local_currency),
        }

    return None