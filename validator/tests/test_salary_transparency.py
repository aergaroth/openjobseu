from app.domain.money.transparency import detect_salary_transparency


def test_salary_disclosed_priority():
    # If salary is detected, it is always 'disclosed' regardless of description
    assert detect_salary_transparency("some text", salary_detected=True) == "disclosed"
    assert detect_salary_transparency("", salary_detected=True) == "disclosed"
    assert detect_salary_transparency(None, salary_detected=True) == "disclosed"


def test_salary_unknown_when_missing():
    # No salary detected and no description -> unknown
    assert detect_salary_transparency(None, salary_detected=False) == "unknown"
    assert detect_salary_transparency("", salary_detected=False) == "unknown"


def test_salary_transparent_statement():
    # Phrases that indicate transparency
    phrases = [
        "salary will be discussed",
        "compensation will be discussed",
        "salary range will be shared",
        "compensation discussed during interview",
        "salary determined based on experience",
    ]
    for phrase in phrases:
        # Exact match (substring)
        assert detect_salary_transparency(f"Note: {phrase}.", salary_detected=False) == "transparent_statement"
        # Case insensitive
        assert detect_salary_transparency(f"Note: {phrase.upper()}.", salary_detected=False) == "transparent_statement"


def test_salary_not_disclosed():
    # Description exists but no keywords
    assert detect_salary_transparency("We offer great coffee and a macbook.", salary_detected=False) == "not_disclosed"
