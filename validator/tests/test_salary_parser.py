import pytest
from app.domain.money.salary_parser import extract_salary


def test_extract_salary_usd_k_format():
    text = "We offer a competitive compensation of $100k - $120k / year."
    result = extract_salary(description=text)
    
    assert result is not None
    assert result["salary_min"] == 100000
    assert result["salary_max"] == 120000
    assert result["salary_currency"] == "USD"
    assert result["salary_period"] == "year"
    # Sprawdzamy czy parser wykonuje też w locie konwersję na EUR
    assert result["salary_min_eur"] is not None
    assert result["salary_max_eur"] is not None


def test_extract_salary_eur_full_format():
    text = "We pay between €60k - €80k annually depending on experience."
    result = extract_salary(description=text)
    
    assert result is not None
    assert result["salary_min"] == 60000
    assert result["salary_max"] == 80000
    assert result["salary_currency"] == "EUR"
    assert result["salary_period"] == "year"


def test_extract_salary_gbp_symbol():
    text = "Salary range is £50,000 - £70,000 per annum"
    result = extract_salary(description=text)
    
    assert result is not None
    assert result["salary_min"] == 50000
    assert result["salary_max"] == 70000
    assert result["salary_currency"] == "GBP"


def test_extract_salary_from_title():
    # Bardzo popularny wzorzec w portalach typu RemoteOK, gdzie pensja jest w tytule
    title = "Senior Python Developer (€80k-€100k)"
    text = "Great opportunity, apply now!"
    
    result = extract_salary(description=text, title=title)
    
    assert result is not None
    assert result["salary_min"] == 80000
    assert result["salary_max"] == 100000
    assert result["salary_currency"] == "EUR"


def test_extract_salary_hourly_rate_not_supported():
    text = "The rate for this contracting role is $50 - $80 / hr."
    result = extract_salary(description=text)
    
    assert result is None


def test_extract_salary_monthly_single_value():
    text = "You will receive 5000 EUR / month."
    result = extract_salary(description=text)
    
    assert result is not None
    assert result["salary_min"] == 5000
    assert result["salary_max"] == 5000
    assert result["salary_currency"] == "EUR"
    assert result["salary_period"] == "month"


def test_extract_salary_no_match():
    text = "Competitive salary and great stock options with remote work budget!"
    result = extract_salary(description=text)
    
    assert result is None