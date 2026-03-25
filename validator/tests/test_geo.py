from app.domain.taxonomy.enums import GeoClass
from app.domain.compliance.classifiers.geo import classify_geo


def test_classify_geo_timezones():
    """Weryfikuje, czy europejskie strefy czasowe w opisie przypisują ofertę do Europy, unikając false-positives."""
    res1 = classify_geo(title="Engineer", description="Working hours are in CET.", remote_scope="")
    assert res1["geo_class"] == GeoClass.EU_REGION
    assert res1["reason"] == "desc_timezone_cet"

    res2 = classify_geo(title="Dev", description="Looking for folks in UTC+1 or UTC+2.", remote_scope="")
    assert res2["geo_class"] == GeoClass.EU_REGION
    assert res2["reason"] == "desc_timezone_utc+1"

    # Ważne: Weryfikacja, czy regex (?![a-z0-9]) chroni przed złapaniem "UTC+10" (Australia) jako "UTC+1"
    res3 = classify_geo(title="Dev", description="We work in UTC+10 (Sydney).", remote_scope="")
    assert res3["geo_class"] == GeoClass.UNKNOWN


def test_classify_geo_eu_region_fallback():
    """Weryfikuje, czy mocne frazy ukryte głęboko w opisie wymuszają klasyfikację EU."""
    res1 = classify_geo(title="Manager", description="This role is Europe-wide.", remote_scope="")
    assert res1["geo_class"] == GeoClass.EU_REGION
    assert res1["reason"] == "desc_europe"

    res2 = classify_geo(title="Manager", description="Must be located within EU.", remote_scope="")
    assert res2["geo_class"] == GeoClass.EU_REGION


def test_classify_geo_uk_safe_fallback():
    """Weryfikuje bezpieczne chwytanie brytyjskich restrykcji w opisie bez fałszywych alarmów dla słowa London."""
    # Jasny wymóg zamieszkania w UK ukryty w tekście chwytany jako UK
    res1 = classify_geo(title="Engineer", description="This is a uk-based role.", remote_scope="")
    assert res1["geo_class"] == GeoClass.UK
    assert res1["reason"] == "desc_uk-based"

    # Samo słowo "London" w opisie (często używane dla określenia np. centrali) nie nadpisuje klasyfikacji
    res2 = classify_geo(title="Engineer", description="Our HQ is in London. Remote globally.", remote_scope="")
    assert res2["geo_class"] == GeoClass.UNKNOWN
