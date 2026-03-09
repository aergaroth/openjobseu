import re
import logging
from typing import Optional, List, Dict
from dataclasses import dataclass, field

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
    "wynagrodzenie", # Polish for remuneration
    "widełki", # Polish for range
]

NEGATIVE_CONTEXT = [
    "years",
    "year experience",
    "years experience",
    "customers",
    "users",
    "downloads",
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

@dataclass
class SalaryMatch:
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    salary_currency: Optional[str] = None
    salary_period: Optional[str] = "year"
    salary_source: str = "regex_v4"
    salary_raw: Optional[str] = None
    salary_min_eur: Optional[float] = None
    salary_max_eur: Optional[float] = None
    salary_confidence: float = 0.0

def normalize_amount(value_str: str) -> int:
    """
    Normalizes a salary string by removing spaces and converting to int.
    Supports spaced thousands like '9 500' -> 9500.
    """
    return int(value_str.replace(" ", ""))

def detect_period_local(text: str) -> str:
    """
    Detects salary period (hour, day, month, year) within a given text window.
    Default is 'year'.
    """
    if "hour" in text:
        return "hour"
    if "day" in text:
        return "day"
    if "month" in text:
        return "month"
    return "year"

def normalize_to_eur(amount: float, currency: str | None) -> float | None:
    """
    Converts an amount to EUR using predefined exchange rates.
    Returns a float.
    """
    if not amount or not currency:
        return None
    
    rate = EXCHANGE_RATES.get(currency.upper())
    if not rate:
        return None
    
    return amount * rate

def is_reasonable_salary(min_val: float, max_val: float, period: str) -> bool:
    """
    Sanity checks for salary ranges. Converts to yearly equivalent for validation.
    Rejects unrealistic values and ratios.
    """
    # 1. Ratio check: max shouldn't be more than 5x min (e.g. 10k-100k is suspicious)
    if min_val and max_val and max_val > min_val * 5:
        return False

    # Normalize to yearly for magnitude check
    multiplier = 1.0
    if period == "month":
        multiplier = 12.0
    elif period == "hour":
        multiplier = 2000.0  # approx working hours per year
    elif period == "day":
        multiplier = 250.0 # approx working days per year

    yearly_min = min_val * multiplier if min_val else 0
    yearly_max = max_val * multiplier if max_max else 0

    # Reasonable yearly range: 15k - 500k EUR/USD equivalent
    # Note: These are rough estimates and might need fine-tuning
    if (yearly_min > 0 and yearly_min < 15000) or (yearly_max > 0 and yearly_max > 500000):
        return False

    return True

def calculate_confidence(salary_match: SalaryMatch, text_window: str, full_text: str) -> float:
    """
    Calculates a confidence score for the extracted salary based on various signals.
    """
    confidence = 0.0
    # +0.4 if currency present
    if salary_match.salary_currency:
        confidence += 0.4
    # +0.3 if range detected
    if salary_match.salary_min is not None and salary_match.salary_max is not None and salary_match.salary_min != salary_match.salary_max:
        confidence += 0.3
    # +0.2 if salary keyword nearby (in the window)
    if any(keyword in text_window for keyword in SALARY_KEYWORDS):
        confidence += 0.2
    # +0.1 if period detected (local)
    if salary_match.salary_period and salary_match.salary_period != "year": 
        confidence += 0.1

    return confidence

def find_salary_windows(text: str, window_size: int = 120) -> List[str]:
    """
    Identifies potential salary-related windows in the text based on keywords.
    """
    windows = []
    # Combined text for keyword search
    text_lower = text.lower()

    found_keywords_indices = []
    for keyword in SALARY_KEYWORDS:
        for match in re.finditer(re.escape(keyword), text_lower):
            found_keywords_indices.append(match.start())
    
    if not found_keywords_indices:
        return [text] # If no keywords, consider the whole text as one window

    # Sort and merge overlapping windows
    found_keywords_indices.sort()
    
    for idx in found_keywords_indices:
        start = max(0, idx - window_size)
        end = min(len(text), idx + window_size)
        windows.append(text[start:end])
    
    # TODO: Implement merging overlapping windows for cleaner processing
    # For now, return possibly overlapping windows
    return windows

def _parse_salary_match(match_text: str, full_text: str) -> Optional[SalaryMatch]:
    """
    Parses a matched salary fragment using various regex patterns.
    """
    salary_match = SalaryMatch(salary_raw=match_text)
    text_lower = match_text.lower()
    
    # Remove common separators for easier number parsing but keep for raw
    clean_text = text_lower.replace(",", "").replace(".", "")
    
    # Regex patterns, ordered by specificity/priority
    patterns = [
        # Range with K and optional currency
        (r"(?:[€$£]|pln|zł)?\s*(\d{2,3})\s?[kK]\s*[-–—]\s*(?:[€$£]|pln|zł)?\s*(\d{2,3})\s?[kK]", 1000, True), 
        # Range with spaced thousands and optional currency
        (r"(?:[€$£]|pln|zł)?\s*(\d[\d\s]{1,})\s*[-–—]\s*(?:[€$£]|pln|zł)?\s*(\d[\d\s]{1,})", 1, True),
        # Fallback with two numbers and currency keyword in between
        (r"(\d[\d\s]{1,})\s*(?:[€$£]|pln|zł)\s*(\d[\d\s]{1,})", 1, True),
        # Single value with K and optional currency
        (r"(?:[€$£]|pln|zł)?\s*(\d{2,3})\s?[kK]\b", 1000, False),
        # Single value with spaced thousands and optional currency
        (r"(?:[€$£]|pln|zł)?\s*(\d[\d\s]{1,})\b", 1, False),
    ]

    for pattern_str, multiplier, is_range in patterns:
        match = re.search(pattern_str, clean_text)
        if match:
            try:
                val1 = normalize_amount(match.group(1)) * multiplier
                if is_range:
                    val2 = normalize_amount(match.group(2)) * multiplier
                    salary_match.salary_min = min(val1, val2)
                    salary_match.salary_max = max(val1, val2)
                else:
                    salary_match.salary_min = val1
                    salary_match.salary_match.salary_max = val1
                
                # Local currency detection within the match
                salary_match.salary_currency = detect_currency(match_text) or detect_currency(full_text)
                salary_match.salary_period = detect_period_local(match_text) # Local period detection

                return salary_match
            except ValueError:
                continue
    
    return None


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


def extract_salary(description: str, title: Optional[str] = None) -> Dict[str, any] | None:
    """
    Main function to extract salary information from job description and title.
    """
    if not description and not title:
        return None

    # Combine description and title for comprehensive scanning
    full_text = f"{title or ''} {description or ''}".lower()
    
    # Find potential salary windows
    salary_windows = find_salary_windows(full_text)

    best_match: Optional[SalaryMatch] = None

    for window in salary_windows:
        # Initial cleaning for regex matching. Preserve raw text for salary_raw
        clean_window = window.replace(",", "").replace(".", "")

        # Try to parse salary from the window
        parsed_match = _parse_salary_match(window, full_text) # Pass the original window for raw and full_text for global currency fallback

        if parsed_match:
            # Sanity checks
            if not is_reasonable_salary(parsed_match.salary_min or 0, parsed_match.salary_max or 0, parsed_match.salary_period or "year"):
                logger.debug(f"Salary rejected by sanity check: {parsed_match}")
                continue
            
            # Calculate confidence
            parsed_match.salary_confidence = calculate_confidence(parsed_match, window, full_text)

            # Reject if confidence is too low
            if parsed_match.salary_confidence < 0.4:
                logger.debug(f"Salary rejected due to low confidence: {parsed_match}")
                continue

            # If multiple matches, take the one with higher confidence
            if not best_match or parsed_match.salary_confidence > best_match.salary_confidence:
                best_match = parsed_match

    if best_match:
        # Final normalization to EUR
        best_match.salary_min_eur = normalize_to_eur(best_match.salary_min or 0, best_match.salary_currency)
        best_match.salary_max_eur = normalize_to_eur(best_match.salary_max or 0, best_match.salary_currency)

        return {
            "salary_min": best_match.salary_min,
            "salary_max": best_match.salary_max,
            "salary_currency": best_match.salary_currency,
            "salary_period": best_match.salary_period,
            "salary_source": best_match.salary_source,
            "salary_raw": best_match.salary_raw,
            "salary_min_eur": best_match.salary_min_eur,
            "salary_max_eur": best_match.salary_max_eur,
            "salary_confidence": best_match.salary_confidence,
        }

    return None

