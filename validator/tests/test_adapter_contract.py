import ast
from pathlib import Path
import pytest

from app.adapters.ats.base import ATSAdapter
from app.adapters.ats.greenhouse import GreenhouseAdapter
from app.adapters.ats.lever import LeverAdapter
from app.adapters.ats.workable import WorkableAdapter
from app.adapters.ats.ashby import AshbyAdapter

ADAPTERS = [
    GreenhouseAdapter(),
    LeverAdapter(),
    WorkableAdapter(),
    AshbyAdapter(),
]


def test_ats_adapters_expose_fetch_and_normalize_methods():
    """Test that all ATS adapters implement required fetch() and normalize() methods."""
    repo_root = Path(__file__).resolve().parents[2]
    adapters_dir = repo_root / "app" / "adapters" / "ats"

    missing_methods: list[str] = []

    for file_path in sorted(adapters_dir.glob("*.py")):
        if file_path.name in {"__init__.py", "base.py", "registry.py"}:
            continue

        tree = ast.parse(file_path.read_text(encoding="utf-8"))

        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue

            method_names = {
                child.name
                for child in node.body
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
            }
            required = {"fetch", "normalize", "probe_jobs"}
            if not required.issubset(method_names):
                missing_methods.append(
                    f"{file_path.relative_to(repo_root)}:{node.lineno}"
                )

    assert not missing_methods, (
        "ATS adapters must implement both fetch() and normalize(). "
        f"Missing in: {', '.join(missing_methods)}"
    )


@pytest.mark.parametrize("adapter", ADAPTERS)
def test_ats_adapter_contract_fields(adapter):
    """Test that adapters implement required contract fields and methods."""
    
    # Check source_name is defined
    assert hasattr(adapter, "source_name"), "Adapter must have source_name attribute"
    assert adapter.source_name, "source_name must not be empty"
    
    # Check backward compatibility with provider
    assert hasattr(adapter, "provider"), "Adapter must have provider property for backward compatibility"
    assert adapter.provider == adapter.source_name, "provider should alias source_name"
    
    # Check normalize_remote_scope method exists
    assert hasattr(adapter, "normalize_remote_scope"), "Adapter must have normalize_remote_scope method"
    
    # Check it's callable
    assert callable(adapter.normalize_remote_scope), "normalize_remote_scope must be callable"


@pytest.mark.parametrize("adapter", ADAPTERS)
def test_normalize_remote_scope_mapping(adapter):
    """Test that normalize_remote_scope correctly maps location strings."""
    
    # Test Europe variants
    assert adapter.normalize_remote_scope("Remote - Europe") == "europe"
    assert adapter.normalize_remote_scope("remote europe") == "europe"
    assert adapter.normalize_remote_scope("EU Remote") == "europe"
    assert adapter.normalize_remote_scope("Remote EU") == "europe"
    assert adapter.normalize_remote_scope("Remote (EU)") == "europe"
    
    # Test worldwide
    assert adapter.normalize_remote_scope("Remote Worldwide") == "worldwide"
    
    # Test empty/None
    assert adapter.normalize_remote_scope(None) == ""
    assert adapter.normalize_remote_scope("") == ""
    assert adapter.normalize_remote_scope("   ") == ""
    
    # Test passthrough for unmapped values
    assert adapter.normalize_remote_scope("New York") == "new york"
    assert adapter.normalize_remote_scope("Berlin, Germany") == "berlin, germany"


VALID_JOBS = [
    (
        GreenhouseAdapter(),
        {
            "id": 12345,
            "title": "Senior Python Developer",
            "content": "<p>We are looking for a senior Python developer...</p>",
            "absolute_url": "https://boards.greenhouse.io/company/jobs/12345",
            "location": {"name": "Remote - Europe"},
            "departments": [{"name": "Engineering"}],
            "updated_at": "2024-01-15T10:00:00Z",
            "_ats_board_token": "test-company",
            "pay_bounds": [
                {
                    "min_value": 80000,
                    "max_value": 100000,
                    "unit": "YEAR"
                }
            ]
        }
    ),
    (
        LeverAdapter(),
        {
            "id": "12345-abc",
            "text": "Senior Python Developer",
            "descriptionPlain": "We are looking for a senior Python developer...",
            "hostedUrl": "https://jobs.lever.co/test-company/12345-abc",
            "categories": {"location": "Remote - Europe", "department": "Engineering"},
            "createdAt": "2024-01-15T10:00:00Z",
            "_ats_slug": "test-company",
            "salaryRange": {
                "min": 90000,
                "max": 110000,
                "currency": "EUR",
                "interval": "per year"
            }
        }
    ),
    (
        WorkableAdapter(),
        {
            "shortcode": "ABC123XYZ",
            "title": "Senior Python Developer",
            "description": "<p>We are looking for a senior Python developer...</p>",
            "url": "https://apply.workable.com/test-company/j/ABC123XYZ/",
            "location": {"country": "Remote - Europe"},
            "department": ["Engineering"],
            "published": "2024-01-15T10:00:00Z",
            "_ats_slug": "test-company",
            "salary": {
                "min": 70000,
                "max": 85000,
                "currency": "GBP",
                "unit": "yearly"
            }
        }
    ),
    (
        AshbyAdapter(),
        {
            "id": "123-ashby-456",
            "title": "Senior Python Developer",
            "descriptionHtml": "<p>We are looking for a senior Python developer...</p>",
            "jobUrl": "https://jobs.ashbyhq.com/test-company/123-ashby-456",
            "location": "Remote - Europe",
            "departmentName": "Engineering",
            "publishedAt": "2024-01-15T10:00:00Z",
            "_ats_slug": "test-company",
            "compensationTier": {
                "minAmount": 100000,
                "maxAmount": 120000,
                "currencyCode": "USD",
                "interval": "year"
            }
        }
    ),
]

@pytest.mark.parametrize("adapter, raw_job", VALID_JOBS)
def test_normalized_job_has_required_fields(adapter, raw_job):
    """Test that normalize() returns a dict with required canonical fields."""
    
    normalized = adapter.normalize(raw_job)
    
    # Required fields
    assert normalized is not None, "normalize() should return a dict for valid job"
    assert "source" in normalized, "Normalized job must have 'source' field"
    assert "source_job_id" in normalized, "Normalized job must have 'source_job_id' field"
    assert "title" in normalized, "Normalized job must have 'title' field"
    assert "description" in normalized, "Normalized job must have 'description' field"
    assert "remote_scope" in normalized, "Normalized job must have 'remote_scope' field"
    
    # Optional but expected fields
    assert "company_name" in normalized, "Normalized job should have 'company_name' field"
    
    # Verify remote_scope was normalized
    assert normalized["remote_scope"] == "europe", "remote_scope should be normalized"
    
    # Verify values
    assert str(normalized["source_job_id"]) in str(raw_job.get("id") or raw_job.get("shortcode"))
    assert normalized["title"] == "Senior Python Developer"
    assert len(normalized["description"]) > 0
    assert normalized.get("department") == "Engineering", "Department should be extracted"
    
    # Extra validation for transparent ATS structured data (e.g. Ashby)
    if raw_job.get("compensationTier"):
        assert normalized["salary_min"] == 100000
        assert normalized["salary_max"] == 120000
        assert normalized["salary_source"] == "ats_api"
    elif raw_job.get("pay_bounds"):
        assert normalized["salary_min"] == 80000
        assert normalized["salary_max"] == 100000
        assert normalized["salary_source"] == "ats_api"
    elif raw_job.get("salaryRange"):
        assert normalized["salary_min"] == 90000
        assert normalized["salary_max"] == 110000
        assert normalized["salary_source"] == "ats_api"
    elif raw_job.get("salary"):
        assert normalized["salary_min"] == 70000
        assert normalized["salary_max"] == 85000
        assert normalized["salary_source"] == "ats_api"


INVALID_JOBS = [
    # Greenhouse missing attributes
    (GreenhouseAdapter(), {"id": 12345, "content": "Description", "absolute_url": "http://example.com", "_ats_board_token": "test"}),
    (GreenhouseAdapter(), {"title": "Developer", "content": "Description", "absolute_url": "http://example.com", "_ats_board_token": "test"}),
    (GreenhouseAdapter(), {"id": 12345, "title": "Developer", "content": "Description", "_ats_board_token": "test"}),
    # Lever missing attributes
    (LeverAdapter(), {"id": "123", "descriptionPlain": "Desc", "hostedUrl": "http://example.com", "_ats_slug": "test"}),
    (LeverAdapter(), {"text": "Developer", "descriptionPlain": "Desc", "hostedUrl": "http://example.com", "_ats_slug": "test"}),
    (LeverAdapter(), {"id": "123", "text": "Developer", "descriptionPlain": "Desc", "_ats_slug": "test"}),
    # Workable missing attributes (URL is optional as workable adapter has a fallback for it)
    (WorkableAdapter(), {"shortcode": "123", "description": "Desc", "url": "http://example.com", "_ats_slug": "test"}),
    (WorkableAdapter(), {"title": "Developer", "description": "Desc", "url": "http://example.com", "_ats_slug": "test"}),
    # Ashby missing attributes
    (AshbyAdapter(), {"id": "123", "descriptionHtml": "Desc", "jobUrl": "http://example.com", "_ats_slug": "test"}),
    (AshbyAdapter(), {"title": "Developer", "descriptionHtml": "Desc", "jobUrl": "http://example.com", "_ats_slug": "test"}),
]

@pytest.mark.parametrize("adapter, raw_job", INVALID_JOBS)
def test_normalized_job_skips_invalid_data(adapter, raw_job):
    """Test that normalize() returns None for invalid/incomplete job data."""
    assert adapter.normalize(raw_job) is None


@pytest.mark.parametrize("adapter", ADAPTERS)
def test_adapter_inheritance(adapter):
    """Test that adapters properly inherit from ATSAdapter base class."""
    assert isinstance(adapter, ATSAdapter), "Adapter must inherit from ATSAdapter"