import logging
from app.domain.money.currency import normalize_to_eur

logger = logging.getLogger(__name__)

SALARY_FIELDS = [
    "salary",
    "salary_range",
    "compensation",
    "compensation_range",
    "base_salary",
    "pay_range",
    "pay",
    "pay_input_ranges",  # Greenhouse
    "salaryRange",       # Lever
]

def extract_structured_salary(job: dict) -> dict | None:
    """
    Attempt to extract salary from structured ATS fields.
    """
    for field in SALARY_FIELDS:
        data = job.get(field)
        if not data:
            continue

        # Handle list of ranges (e.g. Greenhouse sometimes returns a list)
        if isinstance(data, list) and data:
            data = data[0]

        if isinstance(data, dict):
            min_val = data.get("min") or data.get("min_amount") or data.get("minimum")
            max_val = data.get("max") or data.get("max_amount") or data.get("maximum")
            currency = data.get("currency") or data.get("currency_code") or data.get("currencyCode")
            period = data.get("interval") or data.get("period") or data.get("unit")

            # Basic validation
            if not min_val and not max_val:
                continue
            
            try:
                min_val = float(min_val) if min_val is not None else None
                max_val = float(max_val) if max_val is not None else None
            except (ValueError, TypeError):
                continue

            if min_val == 0 and max_val == 0:
                continue

            if currency and isinstance(currency, str):
                currency = currency.upper()
            
            # Normalize period
            if period:
                period = str(period).lower()
                if period in ["hour", "day", "month", "year"]:
                    pass
                else:
                    period = "year" # Default to year if unknown
            else:
                period = "year" # Default to year if not provided

            return {
                "salary_min": min_val,
                "salary_max": max_val,
                "salary_currency": currency,
                "salary_period": period, 
                "salary_source": "structured",
                "salary_min_eur": normalize_to_eur(min_val or 0, currency),
                "salary_max_eur": normalize_to_eur(max_val or 0, currency),
            }

    return None
