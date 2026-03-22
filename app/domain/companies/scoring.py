EU_COUNTRIES = {
    "PL",
    "DE",
    "FR",
    "ES",
    "IT",
    "NL",
    "SE",
    "FI",
    "DK",
    "IE",
    "PT",
    "BE",
    "AT",
    "CZ",
    "SK",
    "HU",
    "RO",
    "BG",
    "HR",
    "SI",
    "LT",
    "LV",
    "EE",
    "LU",
    "MT",
    "CY",
    "GR",
}


class CompanyScoringRules:
    """
    Defines the point values and thresholds for the company signal scoring algorithm.
    Used centrally to evaluate company quality signals.
    """

    REMOTE_ONLY_POINTS = 40
    REMOTE_FRIENDLY_POINTS = 20

    EU_ENTITY_POINTS = 25
    EU_HQ_POINTS = 20

    APPROVAL_RATIO_HIGH_THRESHOLD = 0.8
    APPROVAL_RATIO_HIGH_POINTS = 15

    APPROVAL_RATIO_MID_THRESHOLD = 0.5
    APPROVAL_RATIO_MID_POINTS = 8

    TRANSPARENCY_RATIO_THRESHOLD = 0.5
    TRANSPARENCY_MULTIPLIER = 1.2
