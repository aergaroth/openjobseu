import pytest
from app.domain.taxonomy.taxonomy import classify_taxonomy


class TestClassifyTaxonomyJobFamily:
    def test_software_developer(self):
        result = classify_taxonomy("Senior Software Developer")
        assert result["job_family"] == "software_development"

    def test_backend_engineer(self):
        result = classify_taxonomy("Backend Engineer")
        assert result["job_family"] == "software_development"

    def test_frontend_developer(self):
        result = classify_taxonomy("Frontend Developer")
        assert result["job_family"] == "software_development"

    def test_fullstack_engineer(self):
        result = classify_taxonomy("Fullstack Engineer")
        assert result["job_family"] == "software_development"

    def test_data_scientist(self):
        result = classify_taxonomy("Data Scientist")
        assert result["job_family"] == "data_science"

    def test_data_analyst(self):
        result = classify_taxonomy("Data Analyst")
        assert result["job_family"] == "data_science"

    def test_machine_learning_engineer(self):
        # "engineer" comes first in the check order, so software_development wins
        result = classify_taxonomy("Machine Learning Engineer")
        assert result["job_family"] == "software_development"

    def test_ux_designer(self):
        result = classify_taxonomy("UX Designer")
        assert result["job_family"] == "design"

    def test_graphic_designer(self):
        result = classify_taxonomy("Graphic Designer")
        assert result["job_family"] == "design"

    def test_product_manager(self):
        result = classify_taxonomy("Product Manager")
        assert result["job_family"] == "product_management"

    def test_marketing_specialist(self):
        result = classify_taxonomy("Marketing Specialist")
        assert result["job_family"] == "marketing"

    def test_seo_specialist(self):
        result = classify_taxonomy("SEO Specialist")
        assert result["job_family"] == "marketing"

    def test_sales_representative(self):
        result = classify_taxonomy("Sales Representative")
        assert result["job_family"] == "sales"

    def test_hr_recruiter(self):
        result = classify_taxonomy("HR Recruiter")
        assert result["job_family"] == "hr"

    def test_finance_controller(self):
        result = classify_taxonomy("Finance Controller")
        assert result["job_family"] == "finance"

    def test_operations_coordinator(self):
        result = classify_taxonomy("Operations Coordinator")
        assert result["job_family"] == "operations"

    def test_unknown_title(self):
        result = classify_taxonomy("Chief Happiness Officer")
        assert result["job_family"] == "unknown"


class TestClassifyTaxonomyJobRole:
    def test_engineer(self):
        result = classify_taxonomy("Software Engineer")
        assert result["job_role"] == "engineer"

    def test_developer(self):
        result = classify_taxonomy("Web Developer")
        assert result["job_role"] == "developer"

    def test_data_scientist_role(self):
        result = classify_taxonomy("Data Scientist")
        assert result["job_role"] == "data_scientist"

    def test_designer_role(self):
        result = classify_taxonomy("UX Designer")
        assert result["job_role"] == "designer"

    def test_product_manager_role(self):
        result = classify_taxonomy("Product Manager")
        assert result["job_role"] == "product_manager"

    def test_unknown_role(self):
        result = classify_taxonomy("Chief Happiness Officer")
        assert result["job_role"] == "unknown"


class TestClassifyTaxonomySeniority:
    def test_senior(self):
        result = classify_taxonomy("Senior Developer")
        assert result["seniority"] == "senior"

    def test_lead(self):
        result = classify_taxonomy("Lead Engineer")
        assert result["seniority"] == "senior"

    def test_principal(self):
        result = classify_taxonomy("Principal Architect")
        assert result["seniority"] == "senior"

    def test_staff(self):
        result = classify_taxonomy("Staff Engineer")
        assert result["seniority"] == "senior"

    def test_junior(self):
        result = classify_taxonomy("Junior Developer")
        assert result["seniority"] == "junior"

    def test_associate(self):
        result = classify_taxonomy("Associate Analyst")
        assert result["seniority"] == "junior"

    def test_intern(self):
        result = classify_taxonomy("Software Intern")
        assert result["seniority"] == "junior"

    def test_manager(self):
        result = classify_taxonomy("Engineering Manager")
        assert result["seniority"] == "manager"

    def test_director(self):
        result = classify_taxonomy("Director of Engineering")
        assert result["seniority"] == "manager"

    def test_vp(self):
        result = classify_taxonomy("VP of Product")
        assert result["seniority"] == "manager"

    def test_cto(self):
        result = classify_taxonomy("CTO")
        assert result["seniority"] == "executive"

    def test_chief(self):
        result = classify_taxonomy("Chief Technology Officer")
        assert result["seniority"] == "executive"

    def test_unknown_seniority(self):
        result = classify_taxonomy("Software Developer")
        assert result["seniority"] == "unknown"


class TestClassifyTaxonomySpecialization:
    def test_backend_specialization(self):
        result = classify_taxonomy("Backend Engineer")
        assert result["specialization"] == "backend"

    def test_frontend_specialization(self):
        result = classify_taxonomy("Frontend Developer")
        assert result["specialization"] == "frontend"

    def test_fullstack_specialization(self):
        result = classify_taxonomy("Fullstack Engineer")
        assert result["specialization"] == "fullstack"

    def test_devops_specialization(self):
        result = classify_taxonomy("DevOps Engineer")
        assert result["specialization"] == "devops"

    def test_devsecops_specialization(self):
        result = classify_taxonomy("DevSecOps Engineer")
        assert result["specialization"] == "devsecops"

    def test_kubernetes_devops(self):
        result = classify_taxonomy("Kubernetes Engineer")
        assert result["specialization"] == "devops"

    def test_sre_specialization(self):
        result = classify_taxonomy("SRE")
        assert result["specialization"] == "sre"

    def test_site_reliability_engineer(self):
        result = classify_taxonomy("Site Reliability Engineer")
        assert result["specialization"] == "sre"

    def test_platform_specialization(self):
        result = classify_taxonomy("Platform Engineer")
        assert result["specialization"] == "platform"

    def test_cloud_specialization(self):
        result = classify_taxonomy("Cloud Engineer")
        assert result["specialization"] == "platform"

    def test_infrastructure_specialization(self):
        result = classify_taxonomy("Infrastructure Engineer")
        assert result["specialization"] == "platform"

    def test_machine_learning_specialization(self):
        result = classify_taxonomy("Machine Learning Engineer")
        assert result["specialization"] == "machine_learning"

    def test_ml_specialization(self):
        result = classify_taxonomy("ML Engineer")
        assert result["specialization"] == "machine_learning"

    def test_data_specialization(self):
        result = classify_taxonomy("Data Engineer")
        assert result["specialization"] == "data"

    def test_mobile_ios_specialization(self):
        result = classify_taxonomy("iOS Developer")
        assert result["specialization"] == "mobile"

    def test_mobile_android_specialization(self):
        result = classify_taxonomy("Android Developer")
        assert result["specialization"] == "mobile"

    def test_mobile_keyword_specialization(self):
        result = classify_taxonomy("Mobile Developer")
        assert result["specialization"] == "mobile"

    def test_unknown_specialization(self):
        result = classify_taxonomy("Software Engineer")
        assert result["specialization"] == "unknown"

    # Regression tests for word boundaries
    def test_ml_not_in_html(self):
        """Ensure 'ml' doesn't match in 'HTML Developer'"""
        result = classify_taxonomy("HTML Developer")
        assert result["specialization"] == "unknown"

    def test_ml_not_in_yaml(self):
        """Ensure 'ml' doesn't match in 'YAML Engineer'"""
        result = classify_taxonomy("YAML Configuration Engineer")
        assert result["specialization"] == "unknown"

    def test_data_as_whole_word(self):
        """Ensure 'data' matches as whole word in 'Data Engineer'"""
        result = classify_taxonomy("Data Engineer")
        assert result["specialization"] == "data"

    def test_backend_not_in_feedback(self):
        """Ensure 'backend' doesn't match in unrelated contexts"""
        result = classify_taxonomy("Customer Feedback Analyst")
        assert result["specialization"] == "unknown"

class TestClassifyTaxonomyReturnStructure:
    def test_returns_dict_with_four_keys(self):
        result = classify_taxonomy("Senior Backend Engineer")
        assert set(result.keys()) == {"job_family", "job_role", "seniority", "specialization"}

    def test_all_values_are_strings(self):
        result = classify_taxonomy("Junior Data Analyst")
        for value in result.values():
            assert isinstance(value, str)

    def test_empty_title(self):
        result = classify_taxonomy("")
        assert result["job_family"] == "unknown"
        assert result["job_role"] == "unknown"
        assert result["seniority"] == "unknown"
        assert result["specialization"] == "unknown"

    def test_case_insensitive(self):
        lower = classify_taxonomy("senior software engineer")
        upper = classify_taxonomy("SENIOR SOFTWARE ENGINEER")
        mixed = classify_taxonomy("Senior Software ENGINEER")
        assert lower == upper == mixed


class TestClassifyTaxonomyCombined:
    def test_senior_backend_engineer(self):
        result = classify_taxonomy("Senior Backend Engineer")
        assert result["job_family"] == "software_development"
        assert result["job_role"] == "engineer"
        assert result["seniority"] == "senior"

    def test_junior_frontend_developer(self):
        result = classify_taxonomy("Junior Frontend Developer")
        assert result["job_family"] == "software_development"
        assert result["job_role"] == "developer"
        assert result["seniority"] == "junior"

    def test_lead_data_scientist(self):
        result = classify_taxonomy("Lead Data Scientist")
        assert result["job_family"] == "data_science"
        assert result["job_role"] == "data_scientist"
        assert result["seniority"] == "senior"


class TestDeriveTaxonomy:
    """Test the compute_job_taxonomy wrapper in db_logic."""

    def test_derive_taxonomy_from_job_dict(self):
        from storage.db_logic import compute_job_taxonomy

        job = {"title": "Senior Software Engineer"}
        result = compute_job_taxonomy(job)
        assert result["job_family"] == "software_development"
        assert result["job_role"] == "engineer"
        assert result["seniority"] == "senior"

    def test_derive_taxonomy_missing_title(self):
        from storage.db_logic import compute_job_taxonomy

        job = {}
        result = compute_job_taxonomy(job)
        assert result["job_family"] == "unknown"
        assert result["job_role"] == "unknown"
        assert result["seniority"] == "unknown"
        assert result["specialization"] == "unknown"

    def test_derive_taxonomy_none_title(self):
        from storage.db_logic import compute_job_taxonomy

        job = {"title": None}
        result = compute_job_taxonomy(job)
        assert result["job_family"] == "unknown"
        assert result["job_role"] == "unknown"
        assert result["seniority"] == "unknown"
        assert result["specialization"] == "unknown"
