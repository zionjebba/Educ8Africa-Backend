from pathlib import Path
from fastapi import UploadFile, HTTPException
from app.services.S3Service import upload_file_to_s3

# For avatars (images only)
ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB

# For partnership proposals (documents)
ALLOWED_DOCUMENT_EXTENSIONS = {".pdf", ".doc", ".docx", ".txt", ".ppt", ".pptx", ".xls", ".xlsx"}
MAX_DOCUMENT_SIZE = 10 * 1024 * 1024  # 10MB

async def validate_and_upload_avatar(file: UploadFile, username: str) -> str:
    """
    Validate and upload avatar to S3
    Returns the S3 URL
    """
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(ALLOWED_IMAGE_EXTENSIONS)}"
        )
    
    content = await file.read()
    if len(content) > MAX_IMAGE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size: 5MB"
        )
    
    await file.seek(0)
    
    try:
        s3_url = upload_file_to_s3(
            file,
            folder="uploads/avatars",
            username=username
        )
        return s3_url
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to upload avatar: {str(e)}"
        )

async def validate_and_upload_document(file: UploadFile, identifier: str, document_type: str = "proposal") -> str:
    """
    Validate and upload document to S3
    Returns the S3 URL
    
    Args:
        file: UploadFile object
        identifier: Unique identifier for the file (e.g., organization name)
        document_type: Type of document (e.g., "proposal", "contract")
    """
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_DOCUMENT_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid document type. Allowed: {', '.join(ALLOWED_DOCUMENT_EXTENSIONS)}"
        )
    
    content = await file.read()
    if len(content) > MAX_DOCUMENT_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"Document too large. Maximum size: 10MB"
        )
    
    await file.seek(0)
    
    try:
        s3_url = upload_file_to_s3(
            file,
            folder=f"uploads/documents/{document_type}",
            username=identifier
        )
        return s3_url
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to upload document: {str(e)}"
        )