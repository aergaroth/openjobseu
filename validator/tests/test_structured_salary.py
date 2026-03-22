from app.domain.money.structured_salary import extract_structured_salary


def test_extract_structured_salary_empty():
    assert extract_structured_salary({}) is None
    assert extract_structured_salary({"salary": None}) is None


def test_extract_structured_salary_standard_format():
    job = {"salary": {"min": 100000, "max": 150000, "currency": "usd", "interval": "year"}}
    result = extract_structured_salary(job)
    assert result["salary_min"] == 100000
    assert result["salary_max"] == 150000
    assert result["salary_currency"] == "USD"
    assert result["salary_period"] == "year"
    assert result["salary_source"] == "structured"


def test_extract_structured_salary_list_format_greenhouse():
    job = {
        "pay_input_ranges": [
            {
                "min_amount": "50",
                "max_amount": "80",
                "currency_code": "EUR",
                "unit": "hour",
            }
        ]
    }
    result = extract_structured_salary(job)
    assert result["salary_min"] == 50.0
    assert result["salary_max"] == 80.0
    assert result["salary_currency"] == "EUR"
    assert result["salary_period"] == "hour"


def test_extract_structured_salary_invalid_data():
    # Zeroes should be ignored
    assert extract_structured_salary({"salary": {"min": 0, "max": 0}}) is None

    # Strings that cannot be parsed as floats should be gracefully ignored
    assert extract_structured_salary({"salary": {"min": "negotiable", "max": "DOE"}}) is None


def test_extract_structured_salary_defaults_to_yearly():
    job = {"salaryRange": {"minimum": 90000, "maximum": 120000, "currencyCode": "gbp"}}
    result = extract_structured_salary(job)
    assert result["salary_period"] == "year"  # Default fallback
