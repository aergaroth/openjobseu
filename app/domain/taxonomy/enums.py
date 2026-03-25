from enum import Enum


class JobFamily(str, Enum):
    SOFTWARE_DEVELOPMENT = "software_development"
    DATA_SCIENCE = "data_science"
    DESIGN = "design"
    PRODUCT_MANAGEMENT = "product_management"
    MARKETING = "marketing"
    SALES = "sales"
    HR = "hr"
    FINANCE = "finance"
    OPERATIONS = "operations"
    UNKNOWN = "unknown"


class JobRole(str, Enum):
    ENGINEER = "engineer"
    DEVELOPER = "developer"
    DATA_SCIENTIST = "data_scientist"
    DESIGNER = "designer"
    PRODUCT_MANAGER = "product_manager"
    MARKETING_SPECIALIST = "marketing_specialist"
    SALES_REPRESENTATIVE = "sales_representative"
    HR_SPECIALIST = "hr_specialist"
    FINANCE_ANALYST = "finance_analyst"
    OPERATIONS_MANAGER = "operations_manager"
    UNKNOWN = "unknown"


class Seniority(str, Enum):
    ENTRY_LEVEL = "entry_level"
    JUNIOR = "junior"
    MID_LEVEL = "mid_level"
    SENIOR = "senior"
    LEAD = "lead"
    MANAGER = "manager"
    EXECUTIVE = "executive"
    UNKNOWN = "unknown"


class Specialization(str, Enum):
    BACKEND = "backend"
    FRONTEND = "frontend"
    FULLSTACK = "fullstack"
    DEVOPS = "devops"
    DEVSECOPS = "devsecops"
    PLATFORM = "platform"
    SRE = "sre"
    DATA = "data"
    MACHINE_LEARNING = "machine_learning"
    MOBILE = "mobile"
    UNKNOWN = "unknown"
