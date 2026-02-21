EU_MEMBER_STATES = (
    "austria",
    "belgium",
    "bulgaria",
    "croatia",
    "cyprus",
    "czechia",
    "czech republic",
    "denmark",
    "estonia",
    "finland",
    "france",
    "germany",
    "greece",
    "hungary",
    "ireland",
    "italy",
    "latvia",
    "lithuania",
    "luxembourg",
    "malta",
    "netherlands",
    "poland",
    "portugal",
    "romania",
    "slovakia",
    "slovenia",
    "spain",
    "sweden",
)

EOG_COUNTRIES = (
    "norway",
    "iceland",
    "liechtenstein",
)

EU_REGION_KEYWORDS = (
    "europe",
    "within eu",
    "eu-wide",
    "eu wide",
    "europe-wide",
    "europe wide",
    "europe only",
    "european economic area",
    "eea",
)

UK_KEYWORDS = (
    "united kingdom",
    "uk only",
    "uk-based",
    "uk based",
    "britain",
    "london",
    "england",
    "scotland",
    "wales",
    "northern ireland",
)

US_STRONG_SIGNALS = (
    "united states only",
    "usa only",
    "u.s. only",
    "us only",
    "remote us",
    "remote in the us",
    "remote within the us",
    "remote within united states",
    "us-based only",
    "us based only",
    "u.s.-based only",
    "must live in the us",
    "must be in the us",
    "must reside in the us",
    "must be based in the us",
    "must be us-based",
    "us residents only",
    "within the united states",
    "within united states",
    "u.s.-based",
    "us-based",
    "united states",
    "u.s.",
    "usa",
)

CANADA_STRONG_SIGNALS = (
    "canada only",
    "canadian residents only",
    "remote canada",
    "remote in canada",
    "canada-based",
    "canada based",
    "must live in canada",
    "must be based in canada",
    "must reside in canada",
    "within canada",
    "canada",
)

APAC_STRONG_SIGNALS = (
    "apac only",
    "within apac",
    "asia pacific",
    "apac",
)

AUSTRALIA_STRONG_SIGNALS = (
    "australia only",
    "australia-based",
    "australia based",
    "must live in australia",
    "within australia",
    "australia",
)

INDIA_STRONG_SIGNALS = (
    "india only",
    "india-based",
    "india based",
    "must live in india",
    "within india",
    "india",
)

LATAM_STRONG_SIGNALS = (
    "latam only",
    "within latam",
    "latin america",
    "latam",
)

NON_EU_RESTRICTED = tuple(
    dict.fromkeys(
        (
            *US_STRONG_SIGNALS,
            *CANADA_STRONG_SIGNALS,
            *APAC_STRONG_SIGNALS,
            *AUSTRALIA_STRONG_SIGNALS,
            *INDIA_STRONG_SIGNALS,
            *LATAM_STRONG_SIGNALS,
            "north america only",
        )
    )
)

# Deliberately excludes ambiguous short forms (IN, OR, ME, HI).
US_STATE_CODES = (
    "al",
    "ak",
    "az",
    "ar",
    "ca",
    "co",
    "ct",
    "dc",
    "de",
    "fl",
    "ga",
    "ia",
    "id",
    "il",
    "ks",
    "ky",
    "la",
    "ma",
    "md",
    "mi",
    "mn",
    "mo",
    "ms",
    "mt",
    "nc",
    "nd",
    "ne",
    "nh",
    "nj",
    "nm",
    "nv",
    "ny",
    "oh",
    "ok",
    "pa",
    "ri",
    "sc",
    "sd",
    "tn",
    "tx",
    "ut",
    "va",
    "vt",
    "wa",
    "wi",
    "wv",
    "wy",
)

US_STATE_SIGNAL_THRESHOLD = 3
