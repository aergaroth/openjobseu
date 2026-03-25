from app.domain.taxonomy.taxonomy import classify_taxonomy
from app.domain.taxonomy.enums import JobFamily, JobRole, Seniority, Specialization


def test_classify_taxonomy_default_title_behavior():
    res = classify_taxonomy("Senior Backend Engineer")
    assert res["job_family"] == JobFamily.SOFTWARE_DEVELOPMENT.value
    assert res["job_role"] == JobRole.ENGINEER.value
    assert res["seniority"] == Seniority.SENIOR.value
    assert res["specialization"] == Specialization.BACKEND.value


def test_classify_taxonomy_department_fallback():
    # "Manager" title doesn't indicate a department, but the department field "Sales" does
    res = classify_taxonomy("Manager", department="Sales")
    assert res["job_family"] == JobFamily.SALES.value
    assert res["seniority"] == Seniority.MANAGER.value

    # "Team Lead" in the "Engineering" department
    res2 = classify_taxonomy("Team Lead", department="Engineering")
    assert res2["job_family"] == JobFamily.SOFTWARE_DEVELOPMENT.value


def test_classify_taxonomy_explicit_overrides():
    # Regardless of title, explicitly injected arguments should have the highest priority
    res = classify_taxonomy(
        title="Data Scientist",
        job_family=JobFamily.MARKETING.value,
        job_role=JobRole.MARKETING_SPECIALIST.value,
        seniority=Seniority.JUNIOR.value,
        specialization=Specialization.FRONTEND.value,
    )
    assert res["job_family"] == JobFamily.MARKETING.value
    assert res["job_role"] == JobRole.MARKETING_SPECIALIST.value
    assert res["seniority"] == Seniority.JUNIOR.value
    assert res["specialization"] == Specialization.FRONTEND.value


def test_classify_taxonomy_invalid_explicit_fallback_to_title():
    # If the explicitly provided value is invalid (e.g. "invalid_family"),
    # the function should ignore it and fall back to title-based classification.
    res = classify_taxonomy(
        title="Senior Backend Engineer",
        job_family="invalid_family",
        seniority="super_boss",
    )
    assert res["job_family"] == JobFamily.SOFTWARE_DEVELOPMENT.value
    assert res["seniority"] == Seniority.SENIOR.value


def test_classify_taxonomy_value_error_fallbacks():
    """Cover ValueError fallbacks when instantiating Taxonomy Enums."""
    from app.domain.taxonomy.taxonomy import classify_taxonomy
    from app.domain.taxonomy.enums import JobFamily, JobRole, Seniority, Specialization

    result = classify_taxonomy(
        title="Unknown Job Title",
        department="Unknown Dept",
        job_family="invalid_family",
        job_role="invalid_role",
        seniority="invalid_seniority",
        specialization="invalid_specialization",
    )

    assert result["job_family"] == JobFamily.UNKNOWN.value
    assert result["job_role"] == JobRole.UNKNOWN.value
    assert result["seniority"] == Seniority.UNKNOWN.value
    assert result["specialization"] == Specialization.UNKNOWN.value


def test_normalization_edge_cases():
    """Weryfikuje, czy regex z granicami słów nie ucina prefiksów i sufiksów."""
    from app.domain.taxonomy.taxonomy import _normalize_title

    # Powinno zamienić pełne słowa
    assert _normalize_title("full stack developer") == "fullstack developer"

    # NIE POWINNO uszkodzić słowa 'platforming', choć 'platform' jest na liście mapowań
    assert _normalize_title("platforming engineer") == "platforming engineer"
