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

class AxiUserRole(enum.Enum):
    """Core roles in the AXI ecosystem"""
    # Founders & Leadership
    FOUNDER = "founder"                    # Primary startup founder
    CO_FOUNDER = "co_founder"             # Co-founder of a startup
    
    # Builders & Contributors
    BUILDER = "builder"                    # Technical/creative contributor
    ADVISOR = "advisor"                    # Provides guidance and mentorship
    MENTOR = "mentor"                      # Active mentorship role
    
    # Investors & Partners
    INVESTOR = "investor"                  # Angel/VC investor
    PARTNER = "partner"                    # Strategic partner/organization
    
    # Platform Management
    ADMIN = "admin"                        # Platform administrator
    MODERATOR = "moderator"               # Community moderator
    
    # Default
    UNASSIGNED = "unassigned"             # New user, role pending


class BuilderType(enum.Enum):
    """Specific builder specializations"""
    DEVELOPER = "developer"                # Software developer
    DESIGNER = "designer"                  # UI/UX designer
    MARKETER = "marketer"                 # Marketing specialist
    SALES = "sales"                       # Sales specialist
    PRODUCT_MANAGER = "product_manager"   # Product management
    DATA_ANALYST = "data_analyst"         # Data & analytics
    CONTENT_CREATOR = "content_creator"   # Content creation
    BUSINESS_STRATEGIST = "business_strategist"  # Business strategy
    OPERATIONS = "operations"             # Operations specialist
    FINANCE = "finance"                   # Finance/accounting
    LEGAL = "legal"                       # Legal specialist
    HR = "hr"                            # Human resources
    OTHER = "other"                       # Other specialization


class VerificationStage(enum.Enum):
    """User verification stages"""
    OTP_PENDING = "otp_pending"           # Email/phone OTP not verified
    OTP_VERIFIED = "otp_verified"         # OTP verified, onboarding pending
    ONBOARDING_PENDING = "onboarding_pending"  # Profile completion needed
    PROFILE_COMPLETE = "profile_complete"  # Profile complete, skills pending
    SKILLS_VERIFIED = "skills_verified"   # Skills/portfolio verified
    FULLY_VERIFIED = "fully_verified"     # All verification complete


class AvailabilityStatus(enum.Enum):
    """Builder availability for opportunities"""
    AVAILABLE_FULLTIME = "available_fulltime"      # Available full-time
    AVAILABLE_PARTTIME = "available_parttime"      # Available part-time
    AVAILABLE_FREELANCE = "available_freelance"    # Available for projects
    OPEN_TO_OPPORTUNITIES = "open_to_opportunities"  # Exploring options
    NOT_AVAILABLE = "not_available"                # Not looking
    IN_STARTUP = "in_startup"                      # Currently in a startup


class ExperienceLevel(enum.Enum):
    """Experience level for builders"""
    BEGINNER = "beginner"                 # 0-1 years
    INTERMEDIATE = "intermediate"         # 1-3 years
    ADVANCED = "advanced"                 # 3-5 years
    EXPERT = "expert"                     # 5+ years
    THOUGHT_LEADER = "thought_leader"     # Industry leader


class InvestorType(enum.Enum):
    """Types of investors"""
    ANGEL = "angel"                       # Angel investor
    VC = "vc"                            # Venture capital
    CORPORATE = "corporate"               # Corporate investor
    FAMILY_OFFICE = "family_office"       # Family office
    ACCELERATOR = "accelerator"           # Accelerator/incubator
    GRANT_PROVIDER = "grant_provider"     # Grant organization


class StartupStage(enum.Enum):
    """Startup development stages"""
    IDEA = "idea"                         # Just an idea
    VALIDATION = "validation"             # Validating the idea
    MVP = "mvp"                          # Building MVP
    LAUNCH = "launch"                     # Launching product
    GROWTH = "growth"                     # Growing user base
    SCALE = "scale"                       # Scaling operations
    MATURE = "mature"

class EventStatus(str, enum.Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    CANCELLED = "cancelled"
    COMPLETED = "completed"

class TicketTier(str, enum.Enum):
    REGULAR = "REGULAR"
    VIP = "VIP"
    VVIP = "VVIP"

class TicketStatus(str, enum.Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    USED = "used"

class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class PaymentPurpose(str, enum.Enum):
    EVENT_TICKET = "event_ticket"
    EVENT_SPONSOR = "event_sponsor"
    SUBSCRIPTION = "subscription"
    PRODUCT = "product"
    DISTRIBUTOR_APPLICATION = "distributor_application"
    DISTRIBUTOR_REACTIVATION = "distributor_reactivation"
    OTHER = "other"



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


class DistributorStatus(str, Enum):
    """Distributor application and account status."""
    PENDING = "pending"
    APPROVED = "approved"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    REJECTED = "rejected"


class WithdrawalStatus(str, Enum):
    """Withdrawal request status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    REJECTED = "rejected"


class ProductCategory(str, Enum):
    """Product category types."""
    BEGINNER_KIT = "beginner_kit"
    INNOVATION_KIT = "innovation_kit"
    ADVANCED_KIT = "advanced_kit"
    COMPONENTS = "components"
    SENSORS = "sensors"
    MODULES = "modules"
    ACCESSORIES = "accessories"
    BOOKS = "books"
    OTHER = "other"


class ProductStatus(str, Enum):
    """Product status types."""
    ACTIVE = "active"
    OUT_OF_STOCK = "out_of_stock"
    DISCONTINUED = "discontinued"
    COMING_SOON = "coming_soon"
    DRAFT = "draft"


class PurchaseStatus(str, enum.Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"
