from datetime import timedelta, datetime
from fastapi import APIRouter, Depends, HTTPException, Response, Request
from fastapi.responses import JSONResponse, RedirectResponse
import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from authlib.integrations.starlette_client import OAuth
from dotenv import load_dotenv
import logging

from app.constants.constants import UserRole
from app.core.database import aget_db
from app.core.security import create_jwt_token, decode_jwt_token
from app.core.config import settings
from app.models.user import User

load_dotenv()

logger = logging.getLogger(__name__)

FRONTEND_URL = settings.FRONTEND_URL
MICROSOFT_CLIENT_ID = settings.MICROSOFT_CLIENT_ID
MICROSOFT_CLIENT_SECRET = settings.MICROSOFT_CLIENT_SECRET
MICROSOFT_TENANT_ID = settings.MICROSOFT_TENANT_ID

router = APIRouter(
    prefix="/auth",
    tags=["auth"]
)

# -----------------------------
# OAuth Setup
# -----------------------------
oauth = OAuth()
oauth.register(
    name='microsoft',
    client_id=MICROSOFT_CLIENT_ID,
    client_secret=MICROSOFT_CLIENT_SECRET,
    server_metadata_url=f'https://login.microsoftonline.com/{MICROSOFT_TENANT_ID}/v2.0/.well-known/openid-configuration',
    client_kwargs={
        'scope': 'openid email profile User.Read',
        'token_endpoint_auth_method': 'client_secret_post'
    }
)

# -----------------------------
# Cookie Helpers
# -----------------------------
def set_auth_cookie(response: Response, token: str, expires: timedelta):
    """Set auth cookie."""
    if settings.ENVIRONMENT == "development":
        response.set_cookie(
            key="auth_token",
            value=token,
            httponly=True,
            secure=False,
            samesite="lax",
            domain=settings.COOKIE_DOMAIN,
            path="/",
            max_age=int(expires.total_seconds())
        )
    else:
        response.set_cookie(
            key="auth_token",
            value=token,
            httponly=True,
            secure=True,
            samesite="lax",
            domain=settings.COOKIE_DOMAIN,
            path="/",
            max_age=int(expires.total_seconds())
        )
        existing_cookie = response.headers.get("set-cookie", "")
        if existing_cookie and "Partitioned" not in existing_cookie:
            response.headers["set-cookie"] = existing_cookie + "; Partitioned"

def clear_auth_cookie(response: Response):
    """Clear auth cookie."""
    set_auth_cookie(response, "", timedelta(0))

# -----------------------------
# Microsoft Login
# -----------------------------
@router.get("/microsoft")
async def microsoft_login(request: Request, returnUrl: str = None):
    """
    Initiate Microsoft OAuth login
    """
    try:
        if returnUrl:
            request.session["return_url"] = returnUrl
        
        redirect_uri = request.url_for('microsoft_callback')
        return await oauth.microsoft.authorize_redirect(request, redirect_uri)
    except Exception as e:
        logger.error(f"Microsoft login error: {e}")
        return RedirectResponse(url=f"{FRONTEND_URL}/login?error=connection_failed")

@router.get("/microsoft/callback")
async def microsoft_callback(request: Request, db: AsyncSession = Depends(aget_db)):
    """
    Handle Microsoft OAuth callback
    """
    try:
        token = await oauth.microsoft.authorize_access_token(request)
        
        user_info = token.get('userinfo')
        if not user_info:
            resp = await oauth.microsoft.get('https://graph.microsoft.com/v1.0/me', token=token)
            user_info = resp.json()
        
        return_url = request.session.get("return_url", "/dashboard")
        
        # Extract user info
        email = (
            user_info.get("email") or 
            user_info.get("mail") or 
            user_info.get("userPrincipalName") or
            user_info.get("preferred_username")
        )
        microsoft_id = user_info.get("oid") or user_info.get("sub") or user_info.get("id")
        first_name = user_info.get("givenName") or user_info.get("given_name") or "Unknown"
        last_name = user_info.get("surname") or user_info.get("family_name") or "User"
        
        if not email:
            raise HTTPException(status_code=400, detail="Email not provided by Microsoft")
        
        # Find or create user
        user_query = await db.execute(select(User).where(User.email == email))
        user = user_query.scalar_one_or_none()
        
        if not user:
            user = User(
                email=email,
                first_name=first_name,
                last_name=last_name,
                microsoft_id=microsoft_id,
                is_active=True,
                onboarding_completed=False,
                role=UserRole.employee,
                avatar=None
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)
            onboarding = True
        else:
            if not user.microsoft_id and microsoft_id:
                user.microsoft_id = microsoft_id
            if not user.first_name and first_name:
                user.first_name = first_name
            if not user.last_name and last_name:
                user.last_name = last_name
            await db.commit()
            onboarding = not user.onboarding_completed

        # Create JWT token
        payload = {
            "sub": str(user.user_id),
            "email": user.email,
            "onboarding": onboarding,
            "role": user.role.value if hasattr(user.role, 'value') else user.role,
            "method": "microsoft",
        }
        jwt_token = create_jwt_token(payload, expires_delta=timedelta(hours=8))
        
        request.session["auth_token"] = jwt_token
        request.session["onboarding"] = onboarding
        
        if "return_url" in request.session:
            del request.session["return_url"]
        
        return RedirectResponse(url=f"{settings.BACKEND_URL}/auth/set-cookie?redirect={return_url}")
    
    except Exception as e:
        logger.exception(f"Microsoft callback error: {e}")
        return RedirectResponse(url=f"{FRONTEND_URL}/login?error=auth_failed")

# -----------------------------
# Set Cookie & Redirect
# -----------------------------
@router.get("/set-cookie")
async def set_cookie_and_redirect(request: Request, redirect: str = "/dashboard"):
    """
    Set auth cookie and redirect to frontend
    """
    auth_token = request.session.get("auth_token")
    onboarding = request.session.get("onboarding", False)
    
    if not auth_token:
        return RedirectResponse(url=f"{FRONTEND_URL}/login?error=no_token")
    
    # Clear session
    request.session.pop("auth_token", None)
    request.session.pop("onboarding", None)
    
    # Determine redirect URL
    redirect_url = f"{FRONTEND_URL}/onboarding" if onboarding else f"{FRONTEND_URL}/{redirect.lstrip('/')}"
    
    response = RedirectResponse(url=redirect_url, status_code=303)
    expires = timedelta(hours=8)
    set_auth_cookie(response, auth_token, expires)
    
    return response

# -----------------------------
# Get Current User
# -----------------------------
@router.get("/me")
async def get_current_user(request: Request, response: Response, db: AsyncSession = Depends(aget_db)):
    """
    Return current authenticated user info
    """
    token = request.cookies.get("auth_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        payload = decode_jwt_token(token)
        user_id = payload.get("sub")
        
        from sqlalchemy.orm import joinedload
        result = await db.execute(select(User).options(joinedload(User.department)).where(User.user_id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        
        current_role = user.role.value if hasattr(user.role, 'value') else user.role
        jwt_role = payload.get("role")
        if jwt_role != current_role:
            new_payload = {
                "sub": str(user.user_id),
                "email": user.email,
                "onboarding": not user.onboarding_completed,
                "role": current_role,
                "method": payload.get("method", "microsoft"),
            }
            exp = payload.get("exp")
            if exp:
                remaining_time = datetime.fromtimestamp(exp) - datetime.utcnow()
                if remaining_time.total_seconds() > 300:
                    new_token = create_jwt_token(new_payload, expires_delta=remaining_time)
                    set_auth_cookie(response, new_token, remaining_time)
        
        department_name = user.department.name if user.department else None
        
        return {
            "user_id": str(user.user_id),
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "avatar": user.avatar,
            "onboarding": user.onboarding_completed,
            "role": current_role,
            "department": department_name,
            "is_active": user.is_active,
            "points": user.points,
            "culture_points": user.culture_points,
            "has_read_ceo_message": user.has_read_ceo_message,
            "has_seen_whats_new": user.has_seen_whats_new,
            "phone": user.phone,
            "location": user.location,
            "skills": user.skills,
            "linkedin_url": user.linkedin_url,
            "booking_link": user.booking_link,
        }
    
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        logger.exception(f"Authentication failed: {e}")
        raise HTTPException(status_code=401, detail="Authentication failed")

# -----------------------------
# Mark CEO Message Read
# -----------------------------
@router.patch("/mark-ceo-message-read")
async def mark_ceo_message_read(request: Request, db: AsyncSession = Depends(aget_db)):
    token = request.cookies.get("auth_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = decode_jwt_token(token)
        user_id = payload.get("sub")
        result = await db.execute(select(User).where(User.user_id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        user.has_read_ceo_message = True
        await db.commit()
        await db.refresh(user)
        return {"message": "CEO message marked as read", "has_read_ceo_message": user.has_read_ceo_message}
    except Exception as e:
        await db.rollback()
        logger.exception(f"Error marking CEO message as read: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update user: {str(e)}")

# -----------------------------
# Mark Whats New Seen
# -----------------------------
@router.patch("/mark-whats-new-seen")
async def mark_whats_new_seen(request: Request, db: AsyncSession = Depends(aget_db)):
    token = request.cookies.get("auth_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = decode_jwt_token(token)
        user_id = payload.get("sub")
        result = await db.execute(select(User).where(User.user_id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        user.has_seen_whats_new = True
        await db.commit()
        await db.refresh(user)
        return {"message": "What's new marked as seen", "has_seen_whats_new": user.has_seen_whats_new}
    except Exception as e:
        await db.rollback()
        logger.exception(f"Error marking what's new as seen: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update user: {str(e)}")

# -----------------------------
# Logout
# -----------------------------
@router.post("/logout")
async def logout():
    response = JSONResponse({"message": "Logged out successfully"})
    clear_auth_cookie(response)
    response.headers["Access-Control-Allow-Origin"] = FRONTEND_URL
    response.headers["Access-Control-Allow-Credentials"] = "true"
    return response
