import sys
import os

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

import asyncio
from datetime import datetime
from sqlalchemy import select
from app.core.database import aget_db, session_manager
from app.models.distributor import DistributorApplication, DistributorStatus
import bcrypt
import base64
import hashlib

def hash_password_bcrypt(password: str) -> str:
    """Hash password using bcrypt with proper handling."""
    try:
        # Convert password to bytes and truncate to 72 bytes
        password_bytes = password.encode('utf-8')
        
        if len(password_bytes) > 72:
            # Truncate to 72 bytes
            password_bytes = password_bytes[:72]
            print(f"⚠️ Password truncated to 72 bytes")
        
        # Generate salt and hash
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password_bytes, salt)
        return hashed.decode('utf-8')
    except AttributeError as e:
        # If bcrypt is having issues, use a fallback
        print(f"⚠️ BCrypt error: {e}. Using SHA256 fallback.")
        return hash_password_fallback(password)

def hash_password_fallback(password: str) -> str:
    """Fallback password hashing using SHA256."""
    # Create a salt and hash using SHA256
    salt = "ideotronix_temp_salt_2025_v1"
    combined = f"{password}{salt}{datetime.utcnow().timestamp()}"
    
    # Create SHA256 hash
    sha256_hash = hashlib.sha256(combined.encode('utf-8')).hexdigest()
    
    # Return with identifier
    return f"sha256:{salt}:{sha256_hash}"

async def set_default_passwords():
    """Set default passwords for existing approved distributors."""
    await session_manager.init()
    async for db in aget_db():
        try:
            # Get all approved/active distributors without passwords
            query = select(DistributorApplication).where(
                DistributorApplication.status.in_([
                    DistributorStatus.APPROVED,
                    DistributorStatus.ACTIVE
                ]),
                DistributorApplication.password_hash.is_(None)
            )
            
            result = await db.execute(query)
            distributors = result.scalars().all()
            
            print(f"Found {len(distributors)} distributors without passwords")
            
            updated_count = 0
            for distributor in distributors:
                # Check if distributor has a code
                if not distributor.distributor_code:
                    print(f"⚠️ Skipping {distributor.email}: No distributor code")
                    continue
                
                # Use distributor code as password
                password = distributor.distributor_code
                email = distributor.email
                
                print(f"Processing: {email} with code: {password}")
                
                try:
                    # Try bcrypt first
                    try:
                        password_hash = hash_password_bcrypt(password)
                        print(f"  Using bcrypt hash")
                    except Exception as bcrypt_error:
                        print(f"  BCrypt failed: {bcrypt_error}. Using fallback.")
                        password_hash = hash_password_fallback(password)
                        print(f"  Using fallback hash")
                    
                    # Update the distributor object
                    distributor.password_hash = password_hash
                    distributor.password_set_at = datetime.utcnow()
                    distributor.must_change_password = True
                    distributor.login_attempts = 0
                    distributor.locked_until = None
                    
                    updated_count += 1
                    print(f"✅ Set password for {email}")
                    
                    # Flush periodically to avoid memory issues
                    if updated_count % 10 == 0:
                        await db.flush()
                        
                except Exception as e:
                    print(f"❌ Failed to process {email}: {str(e)}")
                    import traceback
                    traceback.print_exc()
                    continue
            
            if updated_count > 0:
                await db.commit()
                print(f"✅ Successfully set passwords for {updated_count} distributors")
            else:
                await db.commit()
                print("ℹ️ No passwords were set")
            
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            import traceback
            traceback.print_exc()
            await db.rollback()

if __name__ == "__main__":
    asyncio.run(set_default_passwords())