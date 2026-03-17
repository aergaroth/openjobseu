import re
import logging
from typing import Optional, List, Dict
from dataclasses import dataclass

from app.domain.money.currency import detect_currency, normalize_to_eur

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

FUNDING_CONTEXT_PATTERNS = [
    re.compile(r"\d+\s?M", re.IGNORECASE), # 50M, 5M
    re.compile(r"\d+\s?million", re.IGNORECASE),
    re.compile(r"\d+\s?billion", re.IGNORECASE),
]

CURRENCY_CONTEXT_PATTERN = re.compile(r"[€$£]|\b(?:eur|usd|gbp|pln|zł)\b")

SALARY_REGEX_PATTERNS = [
    (re.compile(r"(?:[€$£]|pln|zł)?\s*(\d{1,3}[\s,]?)\s?[kK]\s*[-–—]\s*(?:[€$£]|pln|zł)?\s*(\d{1,3}[\s,]?)\s?[kK]"), 1000, True, "k_range"), 
    (re.compile(r"(?:[€$£]|pln|zł)?\s*(\d[\d\s,]{1,})\s*(?:[€$£]|pln|zł)?\s*[-–—]\s*(?:[€$£]|pln|zł)?\s*(\d[\d\s,]{1,})\s*(?:[€$£]|pln|zł)?"), 1, True, "spaced_thousands_range"),
    (re.compile(r"(\d[\d\s,]{1,})\s*(?:[€$£]|pln|zł)\s+(\d[\d\s,]{1,})"), 1, True, "currency_separated_range"),
    (re.compile(r"(\d[\d\s,]{1,})\s?(?:usd|eur|gbp|pln|zł|€|\$|£)?\s?/?\s?(?:per\s+)?(hour|day|month|year)"), 1, False, "hourly_rate"),
    (re.compile(r"(?:[€$£]|pln|zł)?\s*(\d{1,3}[\s,]?)\s?[kK]\b"), 1000, False, "k_single"),
    (re.compile(r"(?:[€$£]|pln|zł)?\s*(\d[\d\s,]{1,})\b"), 1, False, "spaced_thousands_single"),
]

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
    salary_confidence: int = 0
    pattern_name: Optional[str] = None

def normalize_amount(value_str: str) -> int:
    """
    Normalizes a salary string by removing spaces and converting to int.
    Supports spaced thousands like '9 500' -> 9500.
    Handles commas as thousand separators like '90,000' -> 90000.
    """
    return int(value_str.replace(" ", "").replace(",", ""))

def detect_period_local(text: str, currency: Optional[str] = None) -> str:
    """
    Detects salary period (hour, day, month, year) within a given text window.
    Default is 'year', but can be 'month' for specific currencies like PLN.
    """
    text_lower = text.lower()
    if "hour" in text_lower:
        return "hour"
    if "day" in text_lower:
        return "day"
    if "month" in text_lower:
        return "month"
    if "year" in text_lower:
        return "year"
    
    # Heuristic: For some currencies, 'month' is a safer default if unspecified.
    if currency and currency.upper() == "PLN":
        return "month"

    return "year"

def is_reasonable_salary(min_val: float, max_val: float, period: str, currency: Optional[str] = None) -> bool:
    """
    Sanity checks for salary ranges. Converts to yearly EUR equivalent for validation.
    Rejects unrealistic values and ratios.
    """
    # 1. Ratio check: max shouldn't be more than 5x min (e.g. 10k-100k is suspicious)
    if min_val and max_val and max_val > min_val * 5:
        return False

    # Convert to EUR for magnitude check. If currency is unknown, we can't reliably check.
    min_val_eur = normalize_to_eur(min_val, currency)
    max_val_eur = normalize_to_eur(max_val, currency)

    if min_val_eur is None and max_val_eur is None:
        # Cannot perform magnitude check without currency, but ratio check was done.
        return True

    # Normalize to yearly equivalent
    multiplier = 1.0
    if period == "month":
        multiplier = 12.0
    elif period == "hour":
        multiplier = 2000.0  # approx working hours per year
    elif period == "day":
        multiplier = 250.0 # approx working days per year

    yearly_min = (min_val_eur or 0) * multiplier
    yearly_max = (max_val_eur or 0) * multiplier

    # Reasonable yearly range: 15k - 500k EUR
    if (yearly_min > 0 and yearly_min < 15000) or (yearly_max > 0 and yearly_max > 500000):
        return False

    return True

def is_funding_context(text: str) -> bool:
    """
    Checks if the given text contains patterns indicative of funding amounts (e.g., $50M, 100 million).
    """
    for pattern in FUNDING_CONTEXT_PATTERNS:
        if pattern.search(text):
            return True
    return False

def calculate_confidence(salary_match: SalaryMatch, text_window: str, full_text: str) -> int:
    """
    Calculates a confidence score (0-100) for the extracted salary based on various signals.
    """
    confidence = 0
    # +40 if currency present
    if salary_match.salary_currency:
        confidence += 40
    # +30 if range detected
    if salary_match.salary_min is not None and salary_match.salary_max is not None and salary_match.salary_min != salary_match.salary_max:
        confidence += 30
    # +50 if salary keyword nearby (in the window)
    if any(keyword in text_window for keyword in SALARY_KEYWORDS):
        confidence += 50
    # +10 if period detected (local and not default 'year')
    if "hour" in text_window or "day" in text_window or "month" in text_window or "year" in text_window:
        confidence += 10

    # +10 if 'k' notation is used (strong signal for salary)
    if salary_match.pattern_name in ("k_range", "k_single"):
        confidence += 10

    return confidence

def find_salary_windows(text: str, window_size: int = 120) -> List[str]:
    """
    Identifies potential salary-related windows in the text based on keywords and currency symbols.
    Merges overlapping windows to avoid redundant parsing.
    """
    text_lower = text.lower()
    found_keywords_indices = []
    
    for keyword in SALARY_KEYWORDS:
        for match in re.finditer(re.escape(keyword), text_lower):
            found_keywords_indices.append(match.start())
            
    for match in CURRENCY_CONTEXT_PATTERN.finditer(text_lower):
        found_keywords_indices.append(match.start())
    
    if not found_keywords_indices:
        return []

    found_keywords_indices.sort()
    
    merged_windows = []
    current_start = -1
    current_end = -1
    
    for idx in found_keywords_indices:
        start = max(0, idx - window_size)
        end = min(len(text), idx + window_size)
        
        if current_start == -1:
            current_start = start
            current_end = end
        elif start <= current_end:
            current_end = max(current_end, end)
        else:
            merged_windows.append(text[current_start:current_end])
            current_start = start
            current_end = end
            
    if current_start != -1:
        merged_windows.append(text[current_start:current_end])
    
    return merged_windows

def _parse_salary_match(match_text: str, full_text: str) -> Optional[SalaryMatch]:
    """
    Parses a matched salary fragment using various regex patterns.
    """
    salary_match = SalaryMatch(salary_raw=match_text)
    text_lower = match_text.lower()
    
    for pattern, multiplier, is_range, pattern_name in SALARY_REGEX_PATTERNS:
        match = pattern.search(text_lower) 
        if match:
            try:
                val1_str = match.group(1).replace(" ", "").replace(",", "")
                val1 = int(val1_str) * multiplier
                
                if is_range:
                    val2_str = match.group(2).replace(" ", "").replace(",", "")
                    val2 = int(val2_str) * multiplier
                    salary_match.salary_min = min(val1, val2)
                    salary_match.salary_max = max(val1, val2)
                else:
                    salary_match.salary_min = val1
                    salary_match.salary_max = val1 
                
                salary_match.pattern_name = pattern_name
                
                salary_match.salary_currency = detect_currency(match_text) or detect_currency(full_text)

                if pattern_name == "hourly_rate" and len(match.groups()) > 1:
                    period_str = match.group(2)
                    if period_str:
                        salary_match.salary_period = period_str
                else:
                    salary_match.salary_period = detect_period_local(
                        match_text, salary_match.salary_currency
                    )

                return salary_match
            except ValueError as e:
                logger.debug(f"ValueError during salary parsing: {e} for {match.group(0)}")
                continue
    
    return None

def is_valid_salary_context(text: str, start: int, end: int) -> bool:
    """
    Check surrounding text for positive/negative signals.
    """
    window_start = max(0, start - 40)
    window_end = min(len(text), end + 40)
    window = text[window_start:window_end].lower()

    for word in NEGATIVE_CONTEXT:
        if word in window:
            return False

    if is_funding_context(window):
        return False

    for word in SALARY_KEYWORDS:
        if word in window:
            return True

    # Accept explicit monetary markers even without salary keywords
    if CURRENCY_CONTEXT_PATTERN.search(window):
        return True

    return False

def extract_salary(description: str, title: Optional[str] = None) -> Dict[str, any] | None:
    """
    Main function to extract salary information from job description and title.
    """
    if not description and not title:
        return None

    full_text = f"{title or ''} {description or ''}".lower()
    
    salary_windows = find_salary_windows(full_text)

    best_match: Optional[SalaryMatch] = None

    for window in salary_windows:
        parsed_match = _parse_salary_match(window, full_text) 

        if parsed_match:
            match_idx = full_text.find(parsed_match.salary_raw.lower()) if parsed_match.salary_raw else -1
            if match_idx != -1:
                match_end = match_idx + len(parsed_match.salary_raw)
                if not is_valid_salary_context(full_text, match_idx, match_end):
                    logger.debug(f"Salary rejected by context check: {parsed_match}")
                    continue

            parsed_match.salary_confidence = calculate_confidence(parsed_match, window, full_text)

            if parsed_match.salary_confidence < 40:
                logger.debug(f"Salary rejected due to low confidence: {parsed_match}")
                continue

            if not is_reasonable_salary(parsed_match.salary_min or 0, parsed_match.salary_max or 0, parsed_match.salary_period or "year", parsed_match.salary_currency):
                logger.debug(f"Salary rejected by sanity check: {parsed_match}")
                continue

            if not best_match or parsed_match.salary_confidence > best_match.salary_confidence:
                best_match = parsed_match

    if best_match:
        best_match.salary_min_eur = normalize_to_eur(best_match.salary_min or 0, best_match.salary_currency)
        best_match.salary_max_eur = normalize_to_eur(best_match.salary_max or 0, best_match.salary_currency)

        return {
            "salary_min": int(best_match.salary_min) if best_match.salary_min is not None else None,
            "salary_max": int(best_match.salary_max) if best_match.salary_max is not None else None,
            "salary_currency": best_match.salary_currency,
            "salary_period": best_match.salary_period,
            "salary_source": best_match.salary_source,
            "salary_raw": best_match.salary_raw,
            "salary_min_eur": best_match.salary_min_eur,
            "salary_max_eur": best_match.salary_max_eur,
            "salary_confidence": best_match.salary_confidence,
        }

    return None
