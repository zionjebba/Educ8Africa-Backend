import logging
import os
from fastapi import APIRouter, Depends, Form, UploadFile, File, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import aget_db
from app.core.security import get_current_user
from app.models.user import User
from app.utils.uploads.val_upload_avatar import validate_and_upload_avatar, validate_and_upload_document

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/uploads", tags=["uploads"])

@router.post("/upload-event-image")
async def upload_event_image(
    file: UploadFile = File(...),
    event_name: str = None,
    db: AsyncSession = Depends(aget_db),
    current_user: User = Depends(get_current_user)
):
    """
    Upload event banner/cover image to S3
    Returns the S3 URL for use in event creation/update
    
    Args:
        file: The image file to upload
        event_name: Optional event name for filename prefix
    """
    try:
        logger.info(f"Upload event image request from user: {current_user.user_id}")
        logger.info(f"Content-Type: {file.content_type}")
        logger.info(f"Filename: {file.filename}")
        
        if not file or not file.filename:
            raise HTTPException(status_code=400, detail="No file provided")
        
        # Validate file type
        allowed_types = [
            "image/jpeg", 
            "image/jpg", 
            "image/png", 
            "image/webp",
            "image/pjpeg",
            "image/x-png",
        ]
        
        allowed_extensions = [".jpg", ".jpeg", ".png", ".webp"]
        file_ext = os.path.splitext(file.filename)[1].lower()
        
        is_valid_type = file.content_type in allowed_types if file.content_type else False
        is_valid_ext = file_ext in allowed_extensions
        
        if not (is_valid_type or is_valid_ext):
            logger.error(f"Invalid file type: {file.content_type}, extension: {file_ext}")
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid file type. Only JPEG, PNG, and WebP images are allowed."
            )
        
        # Read and validate file content
        try:
            file_content = await file.read()
            file_size = len(file_content)
            
            logger.info(f"File content read: {file_size} bytes")
            
            if file_size == 0:
                raise HTTPException(status_code=400, detail="Empty file received")
            
            # Allow larger files for event banners (10MB)
            if file_size > 10 * 1024 * 1024:
                raise HTTPException(status_code=400, detail="File too large (max 10MB)")
            
            await file.seek(0)
            
        except Exception as e:
            logger.error(f"Error reading file: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Error reading file: {str(e)}")
        
        # Create meaningful filename prefix
        if event_name:
            # Sanitize event name for filename
            sanitized_name = "".join(c for c in event_name if c.isalnum() or c in (' ', '-', '_')).strip()
            sanitized_name = sanitized_name.replace(' ', '_')[:50]  # Limit length
            filename_prefix = f"event_{sanitized_name}"
        else:
            filename_prefix = f"event_{current_user.user_id}"
        
        logger.info(f"Uploading event image with prefix: {filename_prefix}")
        
        # Use the existing validate_and_upload_avatar function
        # It handles S3 upload and returns the URL
        image_url = await validate_and_upload_avatar(file, filename_prefix)
        
        logger.info(f"Event image uploaded successfully: {image_url}")
        
        return {
            "message": "Event image uploaded successfully",
            "image_url": image_url
        }
    
    except HTTPException as he:
        logger.error(f"HTTP Exception: {he.detail}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error uploading event image: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to upload event image: {str(e)}"
        )


@router.post("/upload-avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(aget_db),
    current_user: User = Depends(get_current_user)
):
    """
    Upload avatar to S3
    Can be used during onboarding or profile updates
    Returns the S3 URL
    """
    try:
        logger.info(f"Upload avatar request for user: {current_user.user_id}")
        logger.info(f"Content-Type: {file.content_type}")
        logger.info(f"Filename: {file.filename}")
        
        if not file or not file.filename:
            raise HTTPException(status_code=400, detail="No file provided")
        
        allowed_types = [
            "image/jpeg", 
            "image/jpg", 
            "image/png", 
            "image/webp",
            "image/pjpeg",
            "image/x-png",
        ]
        
        allowed_extensions = [".jpg", ".jpeg", ".png", ".webp"]
        file_ext = os.path.splitext(file.filename)[1].lower()
        
        is_valid_type = file.content_type in allowed_types if file.content_type else False
        is_valid_ext = file_ext in allowed_extensions
        
        if not (is_valid_type or is_valid_ext):
            logger.error(f"Invalid file type: {file.content_type}, extension: {file_ext}")
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid file type. Content-Type: {file.content_type}, Extension: {file_ext}"
            )
        
        try:
            file_content = await file.read()
            file_size = len(file_content)
            
            logger.info(f"File content read: {file_size} bytes")
            
            if file_size == 0:
                raise HTTPException(status_code=400, detail="Empty file received")
            
            if file_size > 5 * 1024 * 1024:  # 5MB
                raise HTTPException(status_code=400, detail="File too large (max 5MB)")
            
            await file.seek(0)
            
        except Exception as e:
            logger.error(f"Error reading file: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Error reading file: {str(e)}")
        
        username = current_user.first_name or current_user.email.split('@')[0] or f"user_{current_user.user_id}"
        
        logger.info(f"Uploading avatar for username: {username}")
        
        avatar_url = await validate_and_upload_avatar(file, username)
        
        logger.info(f"Avatar uploaded successfully: {avatar_url}")
        
        # Update user avatar in database
        current_user.avatar = avatar_url
        await db.commit()
        await db.refresh(current_user)
        
        logger.info(f"User avatar updated in database")
        
        return {
            "message": "Avatar uploaded successfully",
            "avatar_url": avatar_url
        }
    
    except HTTPException as he:
        logger.error(f"HTTP Exception: {he.detail}")
        await db.rollback()
        raise
    except Exception as e:
        logger.error(f"Unexpected error uploading avatar: {str(e)}", exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to upload avatar: {str(e)}"
        )
    

@router.post("/upload-proposal")
async def upload_proposal_document(
    file: UploadFile = File(...),
    organization_name: str = Form(...),
    db: AsyncSession = Depends(aget_db)
):
    """
    Upload partnership/sponsorship proposal document to S3
    Returns the S3 URL for use in application submission
    
    Args:
        file: The document file to upload (PDF, DOC, DOCX, PPT, PPTX)
        organization_name: Organization name for filename prefix
    """
    try:
        logger.info(f"Upload proposal request for organization: {organization_name}")
        logger.info(f"Content-Type: {file.content_type}")
        logger.info(f"Filename: {file.filename}")
        
        if not file or not file.filename:
            raise HTTPException(status_code=400, detail="No file provided")
        
        # Validate file type - documents only
        allowed_types = [
            "application/pdf",
            "application/msword",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/vnd.ms-powerpoint",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        ]
        
        allowed_extensions = [".pdf", ".doc", ".docx", ".ppt", ".pptx"]
        file_ext = os.path.splitext(file.filename)[1].lower()
        
        is_valid_type = file.content_type in allowed_types if file.content_type else False
        is_valid_ext = file_ext in allowed_extensions
        
        if not (is_valid_type or is_valid_ext):
            logger.error(f"Invalid file type: {file.content_type}, extension: {file_ext}")
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid file type. Only PDF, DOC, DOCX, PPT, and PPTX files are allowed."
            )
        
        # Read and validate file content
        try:
            file_content = await file.read()
            file_size = len(file_content)
            
            logger.info(f"File content read: {file_size} bytes")
            
            if file_size == 0:
                raise HTTPException(status_code=400, detail="Empty file received")
            
            # Allow up to 20MB for proposal documents
            if file_size > 20 * 1024 * 1024:
                raise HTTPException(status_code=400, detail="File too large (max 20MB)")
            
            await file.seek(0)
            
        except Exception as e:
            logger.error(f"Error reading file: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Error reading file: {str(e)}")
        
        # Create meaningful filename prefix
        # Sanitize organization name for filename
        sanitized_name = "".join(c for c in organization_name if c.isalnum() or c in (' ', '-', '_')).strip()
        sanitized_name = sanitized_name.replace(' ', '_')[:50]  # Limit length
        filename_prefix = f"proposal_{sanitized_name}"
        
        logger.info(f"Uploading proposal with prefix: {filename_prefix}")
        
        # Upload document to S3
        proposal_url = await validate_and_upload_document(file, filename_prefix)
        
        logger.info(f"Proposal uploaded successfully: {proposal_url}")
        
        return {
            "message": "Proposal uploaded successfully",
            "proposal_url": proposal_url
        }
    
    except HTTPException as he:
        logger.error(f"HTTP Exception: {he.detail}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error uploading proposal: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to upload proposal: {str(e)}"
        )