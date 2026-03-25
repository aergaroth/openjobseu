import re
from typing import Dict
from .enums import JobFamily, JobRole, Seniority, Specialization


def _compile_rules(rules):
    compiled = []
    for keywords, result in rules:
        # Sortowanie od najdłuższych gwarantuje poprawne zagnieżdżenia w Regexie OR
        sorted_kw = sorted(keywords, key=len, reverse=True)
        pattern = r"\b(?:" + "|".join(re.escape(kw) for kw in sorted_kw) + r")\b"
        compiled.append((re.compile(pattern), result))
    return compiled


# ------------------------------
# UNIFIED COMPILED RULES
# ------------------------------

_RAW_FAMILY_RULES = [
    (["hr", "recruiter", "talent"], JobFamily.HR),
    (["designer", "ux", "ui"], JobFamily.DESIGN),
    (["operations", "support", "office"], JobFamily.OPERATIONS),
    (["product manager", "product owner"], JobFamily.PRODUCT_MANAGEMENT),
    (["marketing", "growth", "seo", "content"], JobFamily.MARKETING),
    (["sales", "account executive", "business development"], JobFamily.SALES),
    (["finance", "accounting", "financial"], JobFamily.FINANCE),
    (
        [
            "developer",
            "development",
            "engineer",
            "engineering",
            "software",
            "backend",
            "frontend",
            "fullstack",
        ],
        JobFamily.SOFTWARE_DEVELOPMENT,
    ),
    (["data scientist", "data"], JobFamily.DATA_SCIENCE),
    (["design"], JobFamily.DESIGN),
]

_RAW_ROLE_RULES_BY_FAMILY = {
    JobFamily.SOFTWARE_DEVELOPMENT: [
        (["engineer", "engineering"], JobRole.ENGINEER),
        (["developer", "development"], JobRole.DEVELOPER),
    ],
    JobFamily.DATA_SCIENCE: [
        (["data scientist", "analyst", "machine learning"], JobRole.DATA_SCIENTIST),
    ],
    JobFamily.DESIGN: [
        (["ux", "ui", "designer"], JobRole.DESIGNER),
    ],
    JobFamily.PRODUCT_MANAGEMENT: [
        (["product manager", "product owner"], JobRole.PRODUCT_MANAGER),
    ],
    JobFamily.MARKETING: [
        (["marketing", "seo", "growth"], JobRole.MARKETING_SPECIALIST),
    ],
    JobFamily.SALES: [
        (["sales", "account"], JobRole.SALES_REPRESENTATIVE),
    ],
    JobFamily.HR: [
        (["recruiter", "hr"], JobRole.HR_SPECIALIST),
    ],
    JobFamily.FINANCE: [
        (["finance", "accounting"], JobRole.FINANCE_ANALYST),
    ],
    JobFamily.OPERATIONS: [
        (["operations", "support"], JobRole.OPERATIONS_MANAGER),
    ],
}

_RAW_SPECIALIZATION_RULES = [
    (["devsecops"], Specialization.DEVSECOPS),
    (
        ["devops", "kubernetes", "terraform", "aws", "gcp", "azure"],
        Specialization.DEVOPS,
    ),
    (["site reliability", "sre"], Specialization.SRE),
    (["platform", "infrastructure", "cloud"], Specialization.PLATFORM),
    (["backend"], Specialization.BACKEND),
    (["frontend"], Specialization.FRONTEND),
    (["fullstack", "full stack"], Specialization.FULLSTACK),
    (["machine learning", "ml"], Specialization.MACHINE_LEARNING),
    (["data"], Specialization.DATA),
    (["ios", "android", "mobile"], Specialization.MOBILE),
]

_RAW_SENIORITY_RULES = [
    (["ceo", "cto", "cfo", "chief"], Seniority.EXECUTIVE),
    (["director", "vp", "head", "manager"], Seniority.MANAGER),
    (["senior", "lead", "principal", "staff"], Seniority.SENIOR),
    (["junior", "associate", "intern"], Seniority.JUNIOR),
]

FAMILY_RULES_COMPILED = _compile_rules(_RAW_FAMILY_RULES)
ROLE_RULES_BY_FAMILY_COMPILED = {k: _compile_rules(v) for k, v in _RAW_ROLE_RULES_BY_FAMILY.items()}
SPECIALIZATION_RULES_COMPILED = _compile_rules(_RAW_SPECIALIZATION_RULES)
SENIORITY_RULES_COMPILED = _compile_rules(_RAW_SENIORITY_RULES)

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
        title = re.sub(rf"\b{re.escape(src)}\b", dst, title)

    return title


def _classify_specialization(title_lower: str) -> Specialization:
    title_lower = _normalize_title(title_lower)
    for pattern, spec in SPECIALIZATION_RULES_COMPILED:
        if pattern.search(title_lower):
            return spec
    return Specialization.UNKNOWN


def _classify_family(title_lower: str) -> JobFamily:
    for pattern, family in FAMILY_RULES_COMPILED:
        if pattern.search(title_lower):
            return family
    return JobFamily.UNKNOWN


def _classify_role(title_lower: str, family: JobFamily) -> JobRole:
    rules = ROLE_RULES_BY_FAMILY_COMPILED.get(family)
    if not rules:
        return JobRole.UNKNOWN

    for pattern, role in rules:
        if pattern.search(title_lower):
            return role

    return JobRole.UNKNOWN


def _classify_seniority(title_lower: str) -> Seniority:
    for pattern, seniority in SENIORITY_RULES_COMPILED:
        if pattern.search(title_lower):
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
