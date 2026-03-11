import ast
from pathlib import Path
import pytest

from app.adapters.ats.base import ATSAdapter
from app.adapters.ats.greenhouse import GreenhouseAdapter


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


def test_ats_adapter_contract_fields():
    """Test that adapters implement required contract fields and methods."""
    # Test with concrete GreenhouseAdapter
    adapter = GreenhouseAdapter()
    
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


def test_normalize_remote_scope_mapping():
    """Test that normalize_remote_scope correctly maps location strings."""
    adapter = GreenhouseAdapter()
    
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


def test_normalized_job_has_required_fields():
    """Test that normalize() returns a dict with required canonical fields."""
    adapter = GreenhouseAdapter()
    
    # Mock raw job data (with _ats_board_token injected by fetch)
    raw_job = {
        "id": 12345,
        "title": "Senior Python Developer",
        "content": "<p>We are looking for a senior Python developer...</p>",
        "absolute_url": "https://boards.greenhouse.io/company/jobs/12345",
        "location": {"name": "Remote - Europe"},
        "updated_at": "2024-01-15T10:00:00Z",
        "_ats_board_token": "test-company",
    }
    
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
    assert normalized["source_job_id"] == "12345"
    assert normalized["title"] == "Senior Python Developer"
    assert len(normalized["description"]) > 0


def test_normalized_job_skips_invalid_data():
    """Test that normalize() returns None for invalid/incomplete job data."""
    adapter = GreenhouseAdapter()
    
    # Missing title
    raw_job_no_title = {
        "id": 12345,
        "content": "Description",
        "absolute_url": "https://example.com/job",
        "_ats_board_token": "test-company",
    }
    assert adapter.normalize(raw_job_no_title) is None
    
    # Missing ID
    raw_job_no_id = {
        "title": "Developer",
        "content": "Description",
        "absolute_url": "https://example.com/job",
        "_ats_board_token": "test-company",
    }
    assert adapter.normalize(raw_job_no_id) is None
    
    # Missing URL
    raw_job_no_url = {
        "id": 12345,
        "title": "Developer",
        "content": "Description",
        "_ats_board_token": "test-company",
    }
    assert adapter.normalize(raw_job_no_url) is None


def test_adapter_inheritance():
    """Test that adapters properly inherit from ATSAdapter base class."""
    adapter = GreenhouseAdapter()
    
    assert isinstance(adapter, ATSAdapter), "Adapter must inherit from ATSAdapter"