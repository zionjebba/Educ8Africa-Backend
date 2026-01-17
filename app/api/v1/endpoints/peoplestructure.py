"""People and Structure router for IAxOS system."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload
from typing import Optional

from app.core.database import aget_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.team import Team, TeamMember
from app.models.department import Department

router = APIRouter(
    prefix="/people-structure",
    tags=["people-structure"]
)


@router.get("/team-directory")
async def get_team_directory(
    search: Optional[str] = Query(None, description="Search by name, title, department, or skills"),
    department_id: Optional[str] = Query(None, description="Filter by department"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(aget_db)
):
    """
    Get all team members with their details for the team directory.
    Supports search and filtering by department.
    Returns members ordered by department hierarchy.
    """
    query = select(User).where(User.is_active == True).options(
        joinedload(User.department)
    )
    
    if department_id:
        query = query.where(User.department_id == department_id)
    
    result = await db.execute(query)
    users = result.unique().scalars().all()
    
    if search:
        search_lower = search.lower()
        users = [
            user for user in users
            if (
                search_lower in user.first_name.lower() or
                search_lower in user.last_name.lower() or
                (user.role and search_lower in user.role.value.lower()) or
                (user.department and search_lower in user.department.name.lower()) or
                (user.skills and search_lower in user.skills.lower())
            )
        ]
    
    team_members = []
    for user in users:
        # Parse skills - handle both JSON array and comma-separated
        skills = []
        if user.skills:
            try:
                # Try to parse as JSON first
                import json
                skills = json.loads(user.skills)
            except (json.JSONDecodeError, TypeError):
                # Fall back to comma-separated
                skills = user.skills.split(',')
                skills = [s.strip() for s in skills if s.strip()]
        
        tags = []
        if user.department:
            tags.append(user.department.name)
        if user.role:
            role_display = user.role.value.replace('_', ' ').title()
            if user.role.value in ['ceo', 'coo', 'department_head', 'team_lead']:
                tags.append("Leadership")
            else:
                tags.append(role_display)
        
        member_data = {
            "id": user.user_id,
            "name": f"{user.first_name} {user.last_name}",
            "title": user.role.value.replace('_', ' ').title() if user.role else "Team Member",
            "department": user.department.name if user.department else "Unassigned",
            "tags": tags,
            "skills": skills,
            "email": user.email,
            "phone": user.phone or "N/A",
            "location": user.location or "Not specified",
            "image": user.avatar or f"https://ui-avatars.com/api/?name={user.first_name}+{user.last_name}&background=random",
        }
        
        # Add optional fields only if they exist
        if user.linkedin_url:
            member_data["linkedin_url"] = user.linkedin_url
        if user.booking_link:
            member_data["booking_link"] = user.booking_link
        
        team_members.append(member_data)
    
    department_order = [
        "Office of the CEO",
        "Research & Development",
        "Business & Strategy",
        "Marketing, Communications & Experience"
    ]
    
    def get_sort_key(member):
        dept = member["department"]
        dept_index = department_order.index(dept) if dept in department_order else 999
        is_ceo = 0 if (dept == "Office of the CEO" and "ceo" in member["title"].lower()) else 1
        return (dept_index, is_ceo, member["name"])
    
    team_members.sort(key=get_sort_key)
    
    return {
        "members": team_members,
        "total": len(team_members)
    }


@router.get("/org-chart")
async def get_org_chart(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(aget_db)
):
    """
    Get organizational chart structure.
    Returns hierarchical organization data starting from CEO.
    """
    ceo_query = await db.execute(
        select(User)
        .where(User.role == 'ceo', User.is_active == True)
        .options(joinedload(User.department))
    )
    ceo = ceo_query.scalar_one_or_none()
    
    if not ceo:
        return {
            "hierarchy": [],
            "message": "No organizational structure defined"
        }
    
    leadership_query = await db.execute(
        select(User)
        .where(
            User.role.in_(['coo', 'department_head']),
            User.is_active == True
        )
        .options(joinedload(User.department))
    )
    leadership = leadership_query.scalars().all()
    
    team_leads_query = await db.execute(
        select(User)
        .where(User.role == 'team_lead', User.is_active == True)
        .options(joinedload(User.department))
    )
    team_leads = team_leads_query.scalars().all()
    
    # Get all teams with their members
    teams_query = await db.execute(
        select(Team)
        .options(
            selectinload(Team.members).joinedload(TeamMember.user),
            joinedload(Team.team_lead)
        )
    )
    teams = teams_query.scalars().all()
    
    def format_user(user):
        return {
            "id": user.user_id,
            "name": f"{user.first_name} {user.last_name}",
            "title": user.role.value.replace('_', ' ').title() if user.role else "Team Member",
            "department": user.department.name if user.department else "Leadership",
            "image": user.avatar or f"https://ui-avatars.com/api/?name={user.first_name}+{user.last_name}&background=random",
            "level": 0
        }
    
    ceo_node = format_user(ceo)
    ceo_node["level"] = 0
    ceo_node["children"] = []
    
    for leader in leadership:
        leader_node = format_user(leader)
        leader_node["level"] = 1
        leader_node["children"] = []
        
        if leader.department_id:
            dept_team_leads = [tl for tl in team_leads if tl.department_id == leader.department_id]
            
            leader_led_teams = [t for t in teams if t.team_lead_id == leader.user_id]
            
            if leader_led_teams:
                for team in leader_led_teams:
                    for team_membership in team.members:
                        member = team_membership.user
                        if member.is_active and member.role not in ['ceo', 'coo', 'department_head', 'team_lead']:
                            member_node = format_user(member)
                            member_node["level"] = 2
                            if not any(child["id"] == member_node["id"] for child in leader_node["children"]):
                                leader_node["children"].append(member_node)
            
            for team_lead in dept_team_leads:
                tl_node = format_user(team_lead)
                tl_node["level"] = 2
                tl_node["children"] = []
                
                led_teams = [t for t in teams if t.team_lead_id == team_lead.user_id]
                
                for team in led_teams:
                    for team_membership in team.members:
                        member = team_membership.user
                        if member.is_active and member.role not in ['ceo', 'coo', 'department_head', 'team_lead']:
                            member_node = format_user(member)
                            member_node["level"] = 3
                            if not any(child["id"] == member_node["id"] for child in tl_node["children"]):
                                tl_node["children"].append(member_node)
                
                leader_node["children"].append(tl_node)
        
        ceo_node["children"].append(leader_node)
    
    return {
        "hierarchy": ceo_node,
        "total_levels": 4
    }


@router.get("/departments")
async def get_departments(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(aget_db)
):
    """
    Get all departments with their teams and team members.
    Shows hierarchical structure: Department > Teams > Members
    """
    departments_query = await db.execute(
        select(Department)
        .options(
            selectinload(Department.teams).selectinload(Team.members).joinedload(TeamMember.user),
            selectinload(Department.teams).joinedload(Team.team_lead),
            joinedload(Department.head),
            selectinload(Department.members)
        )
    )
    departments = departments_query.unique().scalars().all()
    
    dept_data = []
    for dept in departments:
        active_members = [m for m in dept.members if m.is_active]
        
        teams_list = []
        for team in dept.teams:
            team_members = []
            for tm in team.members:
                if tm.user.is_active:
                    team_members.append({
                        "id": tm.user.user_id,
                        "name": f"{tm.user.first_name} {tm.user.last_name}",
                        "role": tm.role_in_team or "Member",
                        "image": tm.user.avatar or f"https://ui-avatars.com/api/?name={tm.user.first_name}+{tm.user.last_name}&background=random"
                    })
            
            teams_list.append({
                "id": team.team_id,
                "name": team.name,
                "description": team.description,
                "lead": {
                    "id": team.team_lead.user_id,
                    "name": f"{team.team_lead.first_name} {team.team_lead.last_name}",
                    "image": team.team_lead.avatar or f"https://ui-avatars.com/api/?name={team.team_lead.first_name}+{team.team_lead.last_name}&background=random"
                } if team.team_lead else None,
                "members": team_members
            })
        
        dept_data.append({
            "id": dept.department_id,
            "name": dept.name,
            "description": dept.description,
            "color": get_department_color(dept.name),
            "head": {
                "id": dept.head.user_id,
                "name": f"{dept.head.first_name} {dept.head.last_name}",
                "title": dept.head.role.value.replace('_', ' ').title() if dept.head.role else "Department Head",
                "image": dept.head.avatar or f"https://ui-avatars.com/api/?name={dept.head.first_name}+{dept.head.last_name}&background=random"
            } if dept.head else None,
            "teams": teams_list,
            "member_count": len(active_members),
            "team_count": len(teams_list)
        })
    
    department_order = [
        "Office of the CEO",
        "Research & Development",
        "Business & Strategy",
        "Marketing, Communications & Experience"
    ]
    
    def get_dept_sort_key(dept):
        name = dept["name"]
        return department_order.index(name) if name in department_order else 999
    
    dept_data.sort(key=get_dept_sort_key)
    
    return {
        "departments": dept_data,
        "total": len(dept_data)
    }


@router.get("/departments/{department_id}")
async def get_department_details(
    department_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(aget_db)
):
    """
    Get detailed information about a specific department.
    """
    dept_query = await db.execute(
        select(Department)
        .where(Department.department_id == department_id)
        .options(
            selectinload(Department.members),
            selectinload(Department.teams).selectinload(Team.members).joinedload(TeamMember.user),
            selectinload(Department.teams).joinedload(Team.team_lead),
            joinedload(Department.head)
        )
    )
    dept = dept_query.unique().scalar_one_or_none()
    
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")
    
    active_members = [m for m in dept.members if m.is_active]
    
    teams_data = []
    for team in dept.teams:
        team_members = []
        for tm in team.members:
            if tm.user.is_active:
                team_members.append({
                    "id": tm.user.user_id,
                    "name": f"{tm.user.first_name} {tm.user.last_name}",
                    "role": tm.role_in_team or "Member",
                    "image": tm.user.avatar or f"https://ui-avatars.com/api/?name={tm.user.first_name}+{tm.user.last_name}&background=random"
                })
        
        teams_data.append({
            "id": team.team_id,
            "name": team.name,
            "description": team.description,
            "members": team_members,
            "lead": {
                "id": team.team_lead.user_id,
                "name": f"{team.team_lead.first_name} {team.team_lead.last_name}",
                "image": team.team_lead.avatar or f"https://ui-avatars.com/api/?name={team.team_lead.first_name}+{team.team_lead.last_name}&background=random"
            } if team.team_lead else None
        })
    
    return {
        "id": dept.department_id,
        "name": dept.name,
        "description": dept.description,
        "mandate": dept.mandate,
        "head": {
            "id": dept.head.user_id,
            "name": f"{dept.head.first_name} {dept.head.last_name}",
            "title": dept.head.role.value.replace('_', ' ').title() if dept.head.role else "Department Head",
            "image": dept.head.avatar or f"https://ui-avatars.com/api/?name={dept.head.first_name}+{dept.head.last_name}&background=random"
        } if dept.head else None,
        "member_count": len(active_members),
        "teams": teams_data,
        "team_count": len(teams_data)
    }


@router.get("/teams")
async def get_teams(
    department_id: Optional[str] = Query(None, description="Filter by department"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(aget_db)
):
    """
    Get all teams with their members.
    Can be filtered by department.
    """
    query = select(Team).options(
        selectinload(Team.members).joinedload(TeamMember.user),
        joinedload(Team.team_lead),
        joinedload(Team.department)
    )
    
    if department_id:
        query = query.where(Team.department_id == department_id)
    
    result = await db.execute(query)
    teams = result.unique().scalars().all()
    
    teams_data = []
    for team in teams:
        members_list = []
        for tm in team.members:
            if tm.user.is_active:
                members_list.append({
                    "id": tm.user.user_id,
                    "name": f"{tm.user.first_name} {tm.user.last_name}",
                    "role": tm.role_in_team or "Member",
                    "image": tm.user.avatar or f"https://ui-avatars.com/api/?name={tm.user.first_name}+{tm.user.last_name}&background=random"
                })
        
        teams_data.append({
            "id": team.team_id,
            "name": team.name,
            "description": team.description,
            "department": team.department.name if team.department else None,
            "lead": {
                "id": team.team_lead.user_id,
                "name": f"{team.team_lead.first_name} {team.team_lead.last_name}",
                "image": team.team_lead.avatar or f"https://ui-avatars.com/api/?name={team.team_lead.first_name}+{team.team_lead.last_name}&background=random"
            } if team.team_lead else None,
            "members": members_list,
            "member_count": len(members_list)
        })
    
    return {
        "teams": teams_data,
        "total": len(teams_data)
    }


@router.get("/user/{user_id}")
async def get_user_profile(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(aget_db)
):
    """
    Get detailed profile information for a specific user.
    """
    user_query = await db.execute(
        select(User)
        .where(User.user_id == user_id, User.is_active == True)
        .options(
            joinedload(User.department),
            selectinload(User.team_memberships).joinedload(TeamMember.team)
        )
    )
    user = user_query.unique().scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    skills = user.skills.split(',') if user.skills else []
    skills = [s.strip() for s in skills if s.strip()]
    
    teams = []
    for tm in user.team_memberships:
        teams.append({
            "id": tm.team.team_id,
            "name": tm.team.name,
            "role": tm.role_in_team or "Member"
        })
    
    return {
        "id": user.user_id,
        "name": f"{user.first_name} {user.last_name}",
        "first_name": user.first_name,
        "last_name": user.last_name,
        "email": user.email,
        "phone": user.phone or "N/A",
        "location": user.location or "Not specified",
        "title": user.role.value.replace('_', ' ').title() if user.role else "Team Member",
        "role": user.role.value if user.role else None,
        "department": {
            "id": user.department.department_id,
            "name": user.department.name
        } if user.department else None,
        "teams": teams,
        "skills": skills,
        "image": user.avatar or f"https://ui-avatars.com/api/?name={user.first_name}+{user.last_name}&background=random",
        "points": user.points,
        "culture_points": user.culture_points
    }


def get_department_color(dept_name: str) -> str:
    """
    Get color for department based on name.
    """
    color_map = {
        "Office of the CEO": "purple",
        "Leadership": "purple",
        "Research & Development": "blue",
        "Engineering": "blue",
        "Business & Strategy": "indigo",
        "Marketing, Communications & Experience": "green",
        "Marketing": "green",
        "Product": "orange",
        "Sales": "red",
        "HR": "pink",
        "Finance": "yellow",
        "Operations": "indigo"
    }
    return color_map.get(dept_name, "gray")