from enum import Enum


class ComplianceStatus(str, Enum):
    APPROVED = "approved"
    REVIEW = "review"
    REJECTED = "rejected"
