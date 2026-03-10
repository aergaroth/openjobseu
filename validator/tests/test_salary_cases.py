import json
import pytest
from pathlib import Path
from app.domain.money.salary_parser import extract_salary

def load_salary_cases():
    path = Path(__file__).parent / "data" / "salary_cases.json"
    with open(path, "r") as f:
        return json.load(f)

@pytest.mark.parametrize("case", load_salary_cases())
def test_salary_parser_cases(case):
    # Extract salary using the updated function
    description = case.get("description") or case.get("text")
    extracted = extract_salary(description=description, title=case.get("title"))
    
    case_label = case.get("text") or f"{case.get('title', '')} {case.get('description', '')}".strip()

    # Assertions
    if case.get("min") is None:
        assert extracted is None, f"Expected no extraction for {case_label}, got {extracted}"
    else:
        assert extracted is not None, f"Expected extraction for {case_label}, got None"
        assert extracted["salary_min"] == case["min"], f"Min mismatch for {case_label}: Expected {case['min']}, got {extracted['salary_min']}"
        assert extracted["salary_max"] == case["max"], f"Max mismatch for {case_label}: Expected {case['max']}, got {extracted['salary_max']}"
        assert extracted["salary_currency"] == case["currency"], f"Currency mismatch for {case_label}: Expected {case['currency']}, got {extracted['salary_currency']}"
        assert extracted["salary_period"] == case["period"], f"Period mismatch for {case_label}: Expected {case['period']}, got {extracted['salary_period']}"
        assert extracted["salary_confidence"] >= case["confidence"], f"Confidence too low for {case_label}: Expected >= {case['confidence']}, got {extracted['salary_confidence']}"

    # Optionally, assert salary_raw
    if extracted and "salary_raw" in extracted and "text" in case:
        # For cases where 'text' is the full input, salary_raw should be a substring
        # For cases with title/description split, salary_raw should match the expected part
        # This might need more specific handling depending on expected raw matches
        pass # For now, we skip strict salary_raw comparison due to complex windowing/regex
