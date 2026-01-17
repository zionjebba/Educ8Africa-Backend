from app.constants.constants import UserRole
from app.models.user import User


def check_manager_role(user: User) -> bool:
    """Check if user has manager/lead permissions."""
    manager_roles = [
        UserRole.ceo, UserRole.coo, UserRole.cto, UserRole.cfo, UserRole.cmo,
        UserRole.department_head, UserRole.team_lead, UserRole.project_manager,
        UserRole.hr_manager
    ]
    return user.role in manager_roles