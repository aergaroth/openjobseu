from app.domain.taxonomy.enums import ComplianceStatus, GeoClass, RemoteClass
from app.domain.compliance.engine import apply_policy


def test_engine_integration_ats_tags_and_timezones():
    """Weryfikuje pełen przepływ dla ofert z ukrytym tagiem ATS i europejską strefą czasową."""
    job = {
        "title": "Backend Developer",
        "remote_scope": "",
        "description": "Must be online during UTC+2. #li-remote",
    }

    result, _ = apply_policy(job, source="test")
    c = result["_compliance"]

    assert c["remote_model"] == RemoteClass.REMOTE_ONLY
    assert c["geo_class"] == GeoClass.EU_REGION
    assert c["compliance_score"] == 100
    assert c["compliance_status"] == ComplianceStatus.APPROVED.value


def test_engine_integration_region_locked_remote_in_text():
    """Weryfikuje pełen przepływ dla ofert z uwarunkowaniem terytorialnym ukrytym wyłącznie w opisie."""
    job = {
        "title": "Data Analyst",
        "remote_scope": "",
        "description": "You will be based remotely in the UK.",
    }

    result, _ = apply_policy(job, source="test")
    c = result["_compliance"]

    assert c["remote_model"] == RemoteClass.REMOTE_REGION_LOCKED
    assert c["geo_class"] == GeoClass.UK
    assert c["compliance_score"] == 90
    assert c["compliance_status"] == ComplianceStatus.APPROVED.value


def test_engine_integration_figma_real_world_case():
    """Weryfikuje faktyczny przypadek z produkcji (Figma) - miasto w scope + region locked w tekście."""
    job = {
        "title": "Account Executive, Enterprise (Berlin, Germany)",
        "remote_scope": "berlin, germany",
        "description": "This is a full time role that can be held from Berlin hub or remotely in Germany.",
    }

    result, _ = apply_policy(job, source="test")
    c = result["_compliance"]

    assert c["remote_model"] == RemoteClass.REMOTE_REGION_LOCKED
    assert c["geo_class"] == GeoClass.EU_MEMBER_STATE
    assert c["compliance_score"] == 90
    assert c["compliance_status"] == ComplianceStatus.APPROVED.value


def test_engine_integration_fivetran_real_world_case():
    """Weryfikuje faktyczny przypadek z produkcji (Fivetran) - zduplikowane miasto + tag LI pisany wielkimi literami."""
    job = {
        "title": "Senior Account Executive",
        "remote_scope": "paris, paris, france",
        # Silnik na etapie klasyfikacji zmniejsza litery, więc sprawdzamy odporność na wielkość liter w oryginale
        "description": "This is a full-time position based remotely in Paris.\n\n#LI-LA1\n#LI-REMOTE",
    }

    result, _ = apply_policy(job, source="test")
    c = result["_compliance"]

    assert c["remote_model"] == RemoteClass.REMOTE_ONLY
    assert c["geo_class"] == GeoClass.EU_MEMBER_STATE
    assert c["compliance_score"] == 100
    assert c["compliance_status"] == ComplianceStatus.APPROVED.value


def test_engine_integration_elastic_real_world_case():
    """Weryfikuje faktyczny przypadek z produkcji (Elastic) - łapanie formy mnogiej 'distributed teams' z opisu."""
    job = {
        "title": "Principal Software Engineer (Networking) - Platform",
        "remote_scope": "spain",
        "description": "Examples of working in distributed teams or working remotely is desirable. As a distributed company...",
    }

    result, _ = apply_policy(job, source="test")
    c = result["_compliance"]

    assert c["remote_model"] == RemoteClass.REMOTE_ONLY
    assert c["geo_class"] == GeoClass.EU_MEMBER_STATE
    assert c["compliance_score"] == 100
    assert c["compliance_status"] == ComplianceStatus.APPROVED.value
