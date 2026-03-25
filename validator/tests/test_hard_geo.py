from app.domain.compliance.classifiers.hard_geo import detect_hard_geo_restriction


def test_hard_geo_canada_restrictions():
    """Weryfikuje, czy twarde wymogi rezydencji w Kanadzie są poprawnie wychwytywane."""
    assert detect_hard_geo_restriction("This role is for Canadian residents only.") is True
    assert detect_hard_geo_restriction("You must reside in Canada to apply.") is True

    # Zwykłe wymienienie Kanady lub elastyczne opcje NIE powinny odpalić twardej blokady
    assert detect_hard_geo_restriction("We have offices in the US, EU, and Canada.") is False
    assert detect_hard_geo_restriction("Eligible to work in the EU or Canada.") is False


def test_hard_geo_apac_restrictions():
    """Weryfikuje blokady nałożone na rynek APAC i azjatycki."""
    assert detect_hard_geo_restriction("Looking for someone in APAC only.") is True
    assert detect_hard_geo_restriction("You must reside in APAC.") is True
    assert detect_hard_geo_restriction("Asia Pacific only.") is True

    # Sama nazwa regionu nie powinna blokować (np. firma obsługująca rynek APAC)
    assert detect_hard_geo_restriction("You will be supporting our APAC clients.") is False


def test_hard_geo_australia_and_india():
    """Weryfikuje blokady dla rynków Australii i Indii."""
    assert detect_hard_geo_restriction("This is an Australia only position.") is True
    assert detect_hard_geo_restriction("Must reside in India.") is True

    # Ponownie, brak wymuszenia nie powinien aktywować reguły
    assert detect_hard_geo_restriction("We are expanding our presence in India.") is False
    assert detect_hard_geo_restriction("Collaborating with teams in Australia.") is False
