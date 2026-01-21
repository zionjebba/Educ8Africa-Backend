"""Constants for user roles, task statuses, leave types, request statuses, event categories, and founder choices."""

from enum import Enum


class UserRole(str, Enum):
    """Enumeration of user roles within the organization."""

    ceo = "ceo"
    coo = "coo"
    cto = "cto"
    cfo = "cfo"
    cmo = "cmo"
    
    # Board & Advisory
    board_member = "board_member"
    advisor = "advisor"
    
    # Management
    department_head = "department_head"
    team_lead = "team_lead"
    project_manager = "project_manager"
    product_manager = "product_manager"
    
    # HR & Admin
    hr_manager = "hr_manager"
    hr_officer = "hr_officer"
    admin = "admin"
    office_manager = "office_manager"
    
    # Finance & Accounting
    financial_officer = "financial_officer"
    accountant = "accountant"
    
    # Technical
    developer = "developer"
    senior_developer = "senior_developer"
    designer = "designer"
    qa_tester = "qa_tester"
    it_support = "it_support"
    
    # Business Functions
    sales = "sales"
    marketing = "marketing"
    business_development = "business_development"
    customer_success = "customer_success"
    legal = "legal"
    
    # Entry Level & Temporary
    employee = "employee"
    intern = "intern"
    nsp = "nsp"  # National Service Personnel
    contractor = "contractor"

class TaskStatus(str, Enum):
    """Enumeration of task statuses."""

    pending = "pending"
    in_progress = "in_progress"
    in_review = "in_review"
    completed = "completed"
    cancelled = "cancelled"
    overdue = "overdue"

class LeaveType(str, Enum):
    """Enumeration of leave types."""

    annual = "annual"
    sick = "sick"
    parental = "parental"
    study = "study"
    unpaid = "unpaid"

class RequestStatus(str, Enum):
    """Enumeration of request statuses."""

    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    cancelled = "cancelled"

class EventCategory(str, Enum):
    """Enumeration of event categories."""

    social = "social"
    learning = "learning"
    celebration = "celebration"
    wellness = "wellness"
    team_building = "team_building"

class FounderChoice(str, Enum):
    """Enumeration of founder choices for company branding."""
    bill_gates = "bill_gates"
    elon_musk = "elon_musk"
    steve_jobs = "steve_jobs"
    custom = "custom"

class AvailabilityCheckStatus(str, Enum):
    pending = "pending"
    confirmed = "confirmed"
    missed = "missed"
    late = "late"

AVAILABLE_ROLES = [
    {
        "value": "employee",
        "label": "Employee",
        "description": "Full-time employee",
        "icon": "briefcase",
        "gradient": "from-blue-500 to-indigo-600",
        "bgPattern": "from-blue-50 to-indigo-50",
        "accentColor": "blue"
    },
    {
        "value": "nsp",
        "label": "NSP",
        "description": "National Service Personnel",
        "icon": "users",
        "gradient": "from-emerald-500 to-teal-600",
        "bgPattern": "from-emerald-50 to-teal-50",
        "accentColor": "emerald"
    },
    {
        "value": "intern",
        "label": "Intern",
        "description": "Ideation Axis Builders Fellow",
        "icon": "lightbulb",
        "gradient": "from-amber-500 to-orange-600",
        "bgPattern": "from-amber-50 to-orange-50",
        "accentColor": "amber"
    },
]

FOUNDER_OPTIONS = [
    {
        "value": "bill_gates",
        "label": "Bill Gates",
        "description": "Co-founder of Microsoft, Philanthropist",
        "image": "/images/founders/bill-gates.png"
    },
    {
        "value": "elon_musk",
        "label": "Elon Musk",
        "description": "CEO of Tesla and SpaceX",
        "image": "/images/founders/elon-musk.png"
    },
    {
        "value": "steve_jobs",
        "label": "Steve Jobs",
        "description": "Co-founder of Apple Inc.",
        "image": "/images/founders/steve-jobs.png"
    },
    {
        "value": "custom",
        "label": "Other",
        "description": "Choose your own inspiration"
    }
]


MISSION_VISSION_CARDS = [
    {
        "id": "mission_card_1",
        "title": "Empowering Founders",
        "description": "To empower African founders to transform bold ideas into world-class ventures that solve real problems and scale globally.",
        "type": "mission"
    },
    {
        "id": "vision_card_1",
        "title": "Global Impact",
        "description": "To become the leading technology hub in Africa by 2030.",
        "type": "vision"
    },
    {
        "id": "mission_card_2",
        "title": "Customer Excellence",
        "description": "Delivering exceptional value through cutting-edge technology and service.",
        "type": "mission"
    }
]

class OrganizationType(str, Enum):
    """Types of organizations for partnerships."""
    startup = "startup"
    corporate = "corporate"
    ngo = "ngo"
    government = "government"
    other = "other"


class SponsorshipTier(str, Enum):
    """Sponsorship tier options."""
    silver = "silver"
    gold = "gold"
    diamond = "diamond"


class SpeakingFormat(str, Enum):
    """Speaking format options."""
    keynote = "keynote"
    panel = "panel"
    fireside_chat = "fireside_chat"
    workshop = "workshop"


class AgeRange(str, Enum):
    """Age range options for volunteers."""
    under_18 = "under_18"
    eighteen_to_22 = "18_22"
    twenty_three_to_30 = "23_30"
    over_30 = "30_plus"


class Availability(str, Enum):
    """Availability options for volunteers."""
    before_event = "before_event"
    event_day = "event_day"
    after_event = "after_event"

ADMIN_EMAILS = ["philipgyimah@ideationaxis.com", "kelvingbolo@ideationaxis.com", "bernardephraim@ideationaxis.com", "kwameyeboah@ideationaxis.com"]
# ADMIN_EMAILS = ["kelvingbolo@ideationaxis.com"]

# models/enums.py
import enum




class EventStatus(str, enum.Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


class JobStatus(str, Enum):
    """Job status enum."""
    DRAFT = "draft"
    OPEN = "open"
    CLOSED = "closed"
    FILLED = "filled"


class ApplicationStatus(str, Enum):
    """Application status enum."""
    PENDING = "pending"
    REVIEWING = "reviewing"
    SHORTLISTED = "shortlisted"
    REJECTED = "rejected"
    ACCEPTED = "accepted"
    WITHDRAWN = "withdrawn"

EDUCATION_ROLES = ["student", "teacher", "parent", "admin"]
EXPERIENCE_LEVELS = ["beginner", "intermediate", "advanced", "expert"]