import sys
import os

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

import asyncio
from datetime import datetime
from sqlalchemy import select, and_
from app.core.database import aget_db, session_manager
from app.models.distributor import DistributorApplication, DistributorStatus
from app.services.MicrosoftGraphClientPublic import MicrosoftGraphClientPublic
from app.core.config import settings

def get_graph_client() -> MicrosoftGraphClientPublic:
    """Create and return a Microsoft Graph Public client instance."""
    return MicrosoftGraphClientPublic(
        tenant_id=settings.MICROSOFT_TENANT_ID,
        client_id=settings.MICROSOFT_CLIENT_ID,
        client_secret=settings.MICROSOFT_CLIENT_SECRET,
        default_sender="ideotronix@ideationaxis.com"
    )

async def send_password_security_notification(distributor_data: dict, graph_client: MicrosoftGraphClientPublic):
    """
    Send password security update notification to distributor.
    """
    email_subject = "🔒 Important Security Update - Your Ideotronix Distributor Account"
    
    email_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 600px;
                margin: 0 auto;
                padding: 20px;
            }}
            .header {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 30px;
                border-radius: 10px 10px 0 0;
                text-align: center;
            }}
            .content {{
                background: #f9f9f9;
                padding: 30px;
                border-radius: 0 0 10px 10px;
            }}
            .info-box {{
                background: white;
                border-left: 4px solid #667eea;
                padding: 15px;
                margin: 20px 0;
                border-radius: 5px;
            }}
            .credentials {{
                background: #fff3cd;
                border: 2px solid #ffc107;
                padding: 20px;
                border-radius: 8px;
                margin: 20px 0;
                text-align: center;
            }}
            .credentials strong {{
                font-size: 18px;
                color: #856404;
            }}
            .warning {{
                background: #f8d7da;
                border-left: 4px solid #dc3545;
                padding: 15px;
                margin: 20px 0;
                border-radius: 5px;
                color: #721c24;
            }}
            .steps {{
                background: white;
                padding: 20px;
                border-radius: 8px;
                margin: 20px 0;
            }}
            .steps ol {{
                padding-left: 20px;
            }}
            .steps li {{
                margin: 10px 0;
                padding: 5px 0;
            }}
            .button {{
                display: inline-block;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 15px 30px;
                text-decoration: none;
                border-radius: 5px;
                margin: 20px 0;
                font-weight: bold;
            }}
            .footer {{
                text-align: center;
                margin-top: 30px;
                padding-top: 20px;
                border-top: 1px solid #ddd;
                color: #666;
                font-size: 12px;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🔒 Security Update</h1>
            <p>Important Information About Your Account</p>
        </div>
        
        <div class="content">
            <p>Dear <strong>{distributor_data['full_name']}</strong>,</p>
            
            <div class="info-box">
                <p><strong>We've Enhanced Your Account Security!</strong></p>
                <p>To better protect your distributor account and earnings, we've implemented password-based authentication for all distributors.</p>
            </div>
            
            <div class="warning">
                <p><strong>⚠️ Action Required:</strong> You must change your password on your first login.</p>
            </div>
            
            <div class="credentials">
                <p><strong>Your Temporary Login Credentials:</strong></p>
                <p style="margin: 15px 0;">
                    <strong>Email:</strong> {distributor_data['email']}<br>
                    <strong>Temporary Password:</strong> <code style="background: #fff; padding: 5px 10px; border-radius: 3px; font-size: 16px;">{distributor_data['distributor_code']}</code>
                </p>
                <p style="font-size: 12px; color: #856404;">⚠️ This is your distributor code. You'll be required to change it immediately after login.</p>
            </div>
            
            <div class="steps">
                <h3>📋 How to Access Your Account:</h3>
                <ol>
                    <li><strong>Visit the distributor login page</strong> at:<br>
                        <a href="https://ideotronix.ideationaxis.com/ideotronix/distributor/dashboard" style="color: #667eea;">https://ideotronix.ideationaxis.com/ideotronix/distributor/dashboard</a>
                    </li>
                    <li><strong>Enter your email</strong> and the temporary password above</li>
                    <li><strong>You'll be prompted</strong> to create a new secure password</li>
                    <li><strong>Choose a strong password</strong> with:
                        <ul>
                            <li>At least 8 characters</li>
                            <li>Mix of uppercase and lowercase letters</li>
                            <li>Numbers and special characters</li>
                        </ul>
                    </li>
                </ol>
            </div>
            
            <div style="text-align: center;">
                <a href="https://ideotronix.ideationaxis.com/ideotronix/distributor/dashboard" class="button">
                    Login to Your Account →
                </a>
            </div>
            
            <div class="info-box">
                <p><strong>🛡️ Why This Change?</strong></p>
                <ul>
                    <li>Enhanced security for your earnings and personal information</li>
                    <li>Protection against unauthorized access</li>
                    <li>Industry-standard authentication practices</li>
                    <li>Better control over your account access</li>
                </ul>
            </div>
            
            <div class="warning">
                <p><strong>Important Security Tips:</strong></p>
                <ul>
                    <li>Never share your password with anyone</li>
                    <li>Use a unique password (don't reuse passwords from other sites)</li>
                    <li>If you forget your password, contact our support team</li>
                    <li>Keep your login credentials secure</li>
                </ul>
            </div>
            
            <p><strong>Need Help?</strong></p>
            <p>If you have any questions or encounter any issues logging in, please don't hesitate to contact us:</p>
            <ul>
                <li>📧 Email: <a href="mailto:ideotronix@ideationaxis.com">ideotronix@ideationaxis.com</a></li>
                <li>📱 WhatsApp: +233 20 109 3855</li>
            </ul>
            
            <p>Thank you for being a valued Ideotronix distributor. We're committed to providing you with a secure and seamless experience.</p>
            
            <p>Best regards,<br>
            <strong>The Ideotronix Team</strong></p>
        </div>
        
        <div class="footer">
            <p>This is an automated security notification from Ideotronix Distributor Portal</p>
            <p>© {datetime.now().year} Ideation Axis. All rights reserved.</p>
        </div>
    </body>
    </html>
    """
    
    try:
        await graph_client.send_email(
            to_emails=[distributor_data['email']],  # Changed from to_email to to_emails (list)
            subject=email_subject,
            body_html=email_body,
            department="distributor_security"
        )
        return True
    except Exception as e:
        print(f"Failed to send email to {distributor_data['email']}: {str(e)}")
        return False

async def notify_all_distributors():
    """
    Send password security notifications to all approved/active distributors.
    """
    await session_manager.init()
    graph_client = get_graph_client()
    
    async for db in aget_db():
        try:
            # Get all approved/active distributors
            query = select(DistributorApplication).where(
                DistributorApplication.status.in_([
                    DistributorStatus.APPROVED,
                    DistributorStatus.ACTIVE
                ])
            )
            
            result = await db.execute(query)
            distributors = result.scalars().all()
            
            print(f"\n{'='*80}")
            print(f"📧 SENDING PASSWORD SECURITY NOTIFICATIONS")
            print(f"{'='*80}")
            print(f"Total distributors to notify: {len(distributors)}\n")
            
            success_count = 0
            failed_count = 0
            
            for distributor in distributors:
                print(f"Processing: {distributor.full_name} ({distributor.email})")
                
                distributor_data = {
                    'full_name': distributor.full_name,
                    'email': distributor.email,
                    'distributor_code': distributor.distributor_code
                }
                
                try:
                    success = await send_password_security_notification(
                        distributor_data=distributor_data,
                        graph_client=graph_client
                    )
                    
                    if success:
                        success_count += 1
                        print(f"  ✅ Email sent successfully")
                    else:
                        failed_count += 1
                        print(f"  ❌ Failed to send email")
                    
                    # Small delay to avoid rate limiting
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    failed_count += 1
                    print(f"  ❌ Error: {str(e)}")
                    continue
            
            print(f"\n{'='*80}")
            print(f"📊 NOTIFICATION SUMMARY")
            print(f"{'='*80}")
            print(f"✅ Successfully sent: {success_count}")
            print(f"❌ Failed: {failed_count}")
            print(f"📧 Total: {len(distributors)}")
            print(f"{'='*80}\n")
            
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    print("\n🚀 Starting Password Security Notification Campaign...\n")
    asyncio.run(notify_all_distributors())
    print("\n✅ Campaign completed!\n")