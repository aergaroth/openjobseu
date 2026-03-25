from app.domain.jobs.enums import RemoteClass
from app.domain.compliance.classifiers.remote import classify_remote


def test_classify_remote_ats_tags():
    """Weryfikuje, czy tagi dodawane przez systemy ATS i frazy o zespołach rozproszonych dają 100% Remote."""
    res1 = classify_remote(title="Engineer", description="Join our distributed team. #LI-Remote", remote_scope="")
    assert res1["remote_model"] == RemoteClass.REMOTE_ONLY
    assert res1["reason"] == "desc_remote_strong"

    res2 = classify_remote(title="Designer", description="We are a fully distributed company.", remote_scope="")
    assert res2["remote_model"] == RemoteClass.REMOTE_ONLY


def test_classify_remote_region_locked_in_description():
    """Weryfikuje, czy uwarunkowania terytorialne ukryte w opisie są poprawnie chwytane jako Region Locked."""
    res1 = classify_remote(title="Developer", description="You will be based remotely in the UK.", remote_scope="")
    assert res1["remote_model"] == RemoteClass.REMOTE_REGION_LOCKED
    assert res1["reason"] == "desc_remote_region_locked"

    res2 = classify_remote(title="Manager", description="Work remotely from Spain.", remote_scope="")
    assert res2["remote_model"] == RemoteClass.REMOTE_REGION_LOCKED


def test_classify_remote_return_to_office_and_onsite():
    """Weryfikuje, czy twarde wymogi pracy biurowej nadpisują fałszywe nadzieje na pracę zdalną."""
    res1 = classify_remote(title="Analyst", description="We are fully onsite now.", remote_scope="")
    assert res1["remote_model"] == RemoteClass.NON_REMOTE

    res2 = classify_remote(title="HR", description="Mandatory return to office starts next month.", remote_scope="")
    assert res2["remote_model"] == RemoteClass.NON_REMOTE

    res3 = classify_remote(
        title="Manager", description="This is an office-only role. No remote options.", remote_scope=""
    )
    assert res3["remote_model"] == RemoteClass.NON_REMOTE

    res4 = classify_remote(title="Developer", description="Great benefits. #LI-Onsite", remote_scope="")
    assert res4["remote_model"] == RemoteClass.NON_REMOTE


def test_classify_remote_not_remote_override():
    """Weryfikuje, czy jawne zaprzeczenia wykluczają ofertę jako NON_REMOTE."""
    res = classify_remote(
        title="Software Engineer", description="Please note this is not a remote position.", remote_scope=""
    )
    assert res["remote_model"] == RemoteClass.NON_REMOTE
    assert res["reason"] == "desc_negative"


def test_classify_remote_hybrid_ats_tags():
    """Weryfikuje, czy tagi hybrydowe z systemów ATS dają NON_REMOTE z odpowiednim powodem."""
    res1 = classify_remote(title="Designer", description="Join our team. #li-hybrid", remote_scope="")
    assert res1["remote_model"] == RemoteClass.NON_REMOTE
    assert res1["reason"] == "hybrid_signal"
