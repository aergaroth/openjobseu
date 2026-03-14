import re
from typing import Dict
from .enums import JobFamily, JobRole, Seniority, Specialization


def _has_word(title_lower: str, word: str) -> bool:
    return bool(re.search(r"\b" + re.escape(word) + r"\b", title_lower))


def _has_any_word(title_lower: str, words: list[str]) -> bool:
    return any(_has_word(title_lower, w) for w in words)


def _has_phrase(title_lower: str, phrase: str) -> bool:
    return phrase in title_lower


# ------------------------------
# FAMILY RULES (order matters)
# ------------------------------

JOB_FAMILY_RULES = [
    (["product manager", "product owner"], JobFamily.PRODUCT_MANAGEMENT),
    (["marketing", "growth", "seo", "content"], JobFamily.MARKETING),
    (["sales", "account executive", "business development"], JobFamily.SALES),
    (["finance", "accounting", "financial"], JobFamily.FINANCE),
    (
        ["developer", "engineer", "software", "backend", "frontend", "fullstack"],
        JobFamily.SOFTWARE_DEVELOPMENT,
    ),
    (["data scientist"], JobFamily.DATA_SCIENCE),
    (["data"], JobFamily.DATA_SCIENCE),
]

# Special rules that use word boundaries (checked before phrase rules)
JOB_FAMILY_WORD_RULES = [
    (["hr", "recruiter", "talent"], JobFamily.HR),
    (["designer", "ux", "ui"], JobFamily.DESIGN),
    (["operations", "support", "office"], JobFamily.OPERATIONS),
]

# Phrase rules for design (after word boundaries to avoid false positives)
JOB_FAMILY_DESIGN_RULES = [
    (["design"], JobFamily.DESIGN),
]


# ------------------------------
# ROLE RULES
# ------------------------------

ROLE_RULES_BY_FAMILY = {
    JobFamily.SOFTWARE_DEVELOPMENT: [
        (["engineer"], JobRole.ENGINEER),
        (["developer"], JobRole.DEVELOPER),
    ],
    JobFamily.DATA_SCIENCE: [
        (["data scientist"], JobRole.DATA_SCIENTIST),
        (["analyst"], JobRole.DATA_SCIENTIST),
        (["machine learning"], JobRole.DATA_SCIENTIST),
    ],
    JobFamily.DESIGN: [
        (["ux"], JobRole.DESIGNER),
        (["ui"], JobRole.DESIGNER),
        (["designer"], JobRole.DESIGNER),
    ],
    JobFamily.PRODUCT_MANAGEMENT: [
        (["product manager"], JobRole.PRODUCT_MANAGER),
        (["product owner"], JobRole.PRODUCT_MANAGER),
    ],
    JobFamily.MARKETING: [
        (["marketing"], JobRole.MARKETING_SPECIALIST),
        (["seo"], JobRole.MARKETING_SPECIALIST),
        (["growth"], JobRole.MARKETING_SPECIALIST),
    ],
    JobFamily.SALES: [
        (["sales"], JobRole.SALES_REPRESENTATIVE),
        (["account"], JobRole.SALES_REPRESENTATIVE),
    ],
    JobFamily.HR: [
        (["recruiter"], JobRole.HR_SPECIALIST),
        (["hr"], JobRole.HR_SPECIALIST),
    ],
    JobFamily.FINANCE: [
        (["finance"], JobRole.FINANCE_ANALYST),
        (["accounting"], JobRole.FINANCE_ANALYST),
    ],
    JobFamily.OPERATIONS: [
        (["operations"], JobRole.OPERATIONS_MANAGER),
        (["support"], JobRole.OPERATIONS_MANAGER),
    ],
}
# ------------------------------
# SPECIALIZATION RULES  (order matters)
# ------------------------------        

SPECIALIZATION_RULES = [
    (["devsecops"], Specialization.DEVSECOPS),
    (["devops", "kubernetes", "terraform", "aws", "gcp", "azure"], Specialization.DEVOPS),
    (["site reliability", "sre"], Specialization.SRE),
    (["platform"], Specialization.PLATFORM),
    (["infrastructure"], Specialization.PLATFORM),
    (["cloud"], Specialization.PLATFORM),

    (["backend"], Specialization.BACKEND),
    (["frontend"], Specialization.FRONTEND),
    (["fullstack", "full stack"], Specialization.FULLSTACK),

    (["machine learning", "ml"], Specialization.MACHINE_LEARNING),
    (["data"], Specialization.DATA),

    (["ios", "android", "mobile"], Specialization.MOBILE),
]

# ------------------------------
# SENIORITY RULES
# ------------------------------

SENIORITY_RULES = [
    (["ceo", "cto", "cfo", "chief"], Seniority.EXECUTIVE),
    (["director", "vp", "head"], Seniority.MANAGER),
    (["manager"], Seniority.MANAGER),
    (["senior", "lead", "principal", "staff"], Seniority.SENIOR),
    (["junior", "associate", "intern"], Seniority.JUNIOR),
]


# ------------------------------
# CLASSIFIERS
# ------------------------------


def _normalize_title(title: str) -> str:
    title = title.lower()

    replacements = {
        "site reliability engineer": "sre",
        "site reliability": "sre",

        "platform engineer": "platform",
        "platform engineering": "platform",

        "cloud engineer": "cloud",
        "cloud infrastructure": "cloud",
        "infrastructure engineer": "infrastructure",

        "dev sec ops": "devsecops",
        "dev-sec-ops": "devsecops",

        "full stack": "fullstack",
        "front end": "frontend",
        "back end": "backend",
    }

    for src, dst in replacements.items():
        title = title.replace(src, dst)

    return title

def _classify_specialization(title_lower: str) -> Specialization:
    title_lower = _normalize_title(title_lower)
    for keywords, spec in SPECIALIZATION_RULES:
        for kw in keywords:
            # Use word boundaries for single words, phrase matching for multi-word terms
            if " " in kw:
                # Multi-word phrase - use exact phrase matching
                if kw in title_lower:
                    return spec
            else:
                # Single word - use word boundary matching
                if _has_word(title_lower, kw):
                    return spec
    return Specialization.UNKNOWN


def _classify_family(title_lower: str) -> JobFamily:
    # First check word-boundary rules (more strict, prevents false positives)
    for keywords, family in JOB_FAMILY_WORD_RULES:
        if _has_any_word(title_lower, keywords):
            return family
    
    # Then check phrase-based rules
    for keywords, family in JOB_FAMILY_RULES:
        for kw in keywords:
            if _has_phrase(title_lower, kw):
                return family
    
    # Finally check design phrase rules
    for keywords, family in JOB_FAMILY_DESIGN_RULES:
        for kw in keywords:
            if _has_phrase(title_lower, kw):
                return family
    
    return JobFamily.UNKNOWN


def _classify_role(title_lower: str, family: JobFamily) -> JobRole:
    rules = ROLE_RULES_BY_FAMILY.get(family)
    if not rules:
        return JobRole.UNKNOWN

    for keywords, role in rules:
        if _has_any_word(title_lower, keywords):
            return role

    return JobRole.UNKNOWN


def _classify_seniority(title_lower: str) -> Seniority:
    for keywords, seniority in SENIORITY_RULES:
        if _has_any_word(title_lower, keywords):
            return seniority
    return Seniority.UNKNOWN


# ------------------------------
# PUBLIC API
# ------------------------------

def classify_taxonomy(
    title: str,
    department: str | None = None,
    job_family: str | None = None,
    job_role: str | None = None,
    seniority: str | None = None,
    specialization: str | None = None,
) -> Dict[str, str]:
    title_lower = title.lower()

    family = JobFamily.UNKNOWN
    if job_family:
        try:
            family = JobFamily(job_family)
        except ValueError:
            pass

    if family == JobFamily.UNKNOWN and department:
        family = _classify_family(department.lower())

    if family == JobFamily.UNKNOWN:
        family = _classify_family(title_lower)

    role = JobRole.UNKNOWN
    if job_role:
        try:
            role = JobRole(job_role)
        except ValueError:
            pass

    if role == JobRole.UNKNOWN:
        role = _classify_role(title_lower, family)

    resolved_seniority = Seniority.UNKNOWN
    if seniority:
        try:
            resolved_seniority = Seniority(seniority)
        except ValueError:
            pass

    if resolved_seniority == Seniority.UNKNOWN:
        resolved_seniority = _classify_seniority(title_lower)

    spec = Specialization.UNKNOWN
    if specialization:
        try:
            spec = Specialization(specialization)
        except ValueError:
            pass

    if spec == Specialization.UNKNOWN:
        spec = _classify_specialization(title_lower)
    
    return {
        "job_family": family.value,
        "job_role": role.value,
        "seniority": resolved_seniority.value,
        "specialization": spec.value,
    }
