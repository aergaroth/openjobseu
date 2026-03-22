TRANSPARENCY_PHRASES = [
    "salary will be discussed",
    "compensation will be discussed",
    "salary range will be shared",
    "compensation discussed during interview",
    "salary determined based on experience",
]


def detect_salary_transparency(description: str, salary_detected: bool) -> str:
    """
    Detect if the job offer discloses salary, has a transparency statement, or hides it.
    Returns: disclosed | transparent_statement | not_disclosed | unknown
    """
    if salary_detected:
        return "disclosed"

    if not description:
        return "unknown"

    text = description.lower()

    for phrase in TRANSPARENCY_PHRASES:
        if phrase in text:
            return "transparent_statement"

    return "not_disclosed"
