from app.domain.jobs.enums import GeoClass, RemoteClass
from app.domain.compliance.classifiers.enums import ComplianceStatus
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


def test_engine_integration_distributed_teams_plural_not_remote():
    """Regresja: 'distributed teams' (mnoga) NIE może triggerować REMOTE_ONLY.

    Bug: 'distributed team' jako substring matchował 'distributed teams',
    dając fałszywy REMOTE_ONLY dla biurowych ofert (np. Stripe Dublin, N26 Berlin).
    Po naprawie word-boundary matching forma mnoga jest ignorowana.
    """
    job = {
        "title": "Engineering Manager - Fraud Risk",
        "remote_scope": "dublin",
        "description": "Experience working with distributed teams and remote colleagues. Lead and grow an engineering team in Dublin.",
    }

    result, _ = apply_policy(job, source="test")
    c = result["_compliance"]

    assert c["remote_model"] != RemoteClass.REMOTE_ONLY, "distributed teams (plural) should not trigger REMOTE_ONLY"
    assert c["compliance_score"] < 80, "office-based Dublin role should not appear in public feed"


def test_engine_integration_work_from_home_budget_not_remote():
    """Regresja: 'work from home budget' (benefit) NIE może triggerować REMOTE_ONLY.

    Bug: opis N26 zawierał 'work from home budget' jako benefit → fałszywy REMOTE_ONLY
    dla wszystkich 38 biurowych ofert N26 (Berlin/Barcelona/Madrid).
    """
    job = {
        "title": "ICT GRC - Firewall Governance Manager",
        "remote_scope": "berlin",
        "description": "Join our Berlin team. Benefits include: work from home budget, health insurance, and gym membership.",
    }

    result, _ = apply_policy(job, source="test")
    c = result["_compliance"]

    assert c["remote_model"] != RemoteClass.REMOTE_ONLY, (
        "work from home budget (benefit) should not trigger REMOTE_ONLY"
    )
    assert c["compliance_score"] < 80, "office-based Berlin role should not appear in public feed"


def test_engine_integration_elastic_real_world_case():
    """Weryfikuje faktyczny przypadek z produkcji (Elastic) - poprawne wykrywanie remote przez #LI-Remote.

    Elastic taguje oferty jako remote przez #LI-Remote w opisie.
    Poprzednio test opierał się na fałszywym sygnale 'distributed teams' (forma mnoga),
    który był substringing 'distributed team'. Po naprawie word-boundary matching
    wymagany jest prawdziwy sygnał remote — tak jak w rzeczywistych ofertach Elastic.
    """
    job = {
        "title": "Principal Software Engineer (Networking) - Platform",
        "remote_scope": "spain",
        "description": "Examples of working in distributed teams or working remotely is desirable. As a distributed company we rely on many tools to coordinate. #LI-Remote",
    }

    result, _ = apply_policy(job, source="test")
    c = result["_compliance"]

    assert c["remote_model"] == RemoteClass.REMOTE_ONLY
    assert c["geo_class"] == GeoClass.EU_MEMBER_STATE
    assert c["compliance_score"] == 100
    assert c["compliance_status"] == ComplianceStatus.APPROVED.value
