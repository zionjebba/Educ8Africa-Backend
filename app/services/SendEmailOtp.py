# services/email_service.py

from app.services.MicrosoftGraphClientPublic import MicrosoftGraphClientPublic
from app.core.config import settings


# Initialize Microsoft Graph Client
graph_client = MicrosoftGraphClientPublic(
    tenant_id=settings.MICROSOFT_TENANT_ID,
    client_id=settings.MICROSOFT_CLIENT_ID,
    client_secret=settings.MICROSOFT_CLIENT_SECRET,
    default_sender="axi@ideationaxis.com"
)


async def send_email_otp(email: str, code: str):
    """
    Send OTP verification code via email using Microsoft Graph API.
    
    Args:
        email: Recipient email address
        code: 6-digit OTP code
    
    Returns:
        dict with status information
    """
    
    # Email template HTML
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: linear-gradient(135deg, #0A2463 0%, #1e40af 100%); color: white; padding: 30px; border-radius: 10px 10px 0 0; text-align: center; }}
            .content {{ background: #f9fafb; padding: 40px 30px; border-radius: 0 0 10px 10px; }}
            .otp-box {{ background: white; padding: 30px; border-radius: 8px; margin: 30px 0; text-align: center; border: 2px solid #ffc007; }}
            .otp-code {{ font-size: 36px; font-weight: bold; color: #0A2463; letter-spacing: 8px; font-family: 'Courier New', monospace; }}
            .warning-box {{ background: #fef3c7; padding: 15px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #f59e0b; }}
            .footer {{ text-align: center; margin-top: 30px; color: #6b7280; font-size: 12px; }}
            .logo {{ width: 80px; margin-bottom: 15px; }}
            h1 {{ margin: 0; font-size: 24px; }}
            .expires {{ color: #6b7280; font-size: 14px; margin-top: 10px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <img src="https://ideationaxis.com/logos/white-logo.png" alt="Ideation Axis" class="logo" />
                <h1>🔐 Verification Code</h1>
            </div>
            <div class="content">
                <p>Hello,</p>
                <p>Your verification code for <strong>Axi</strong> is:</p>
                
                <div class="otp-box">
                    <div class="otp-code">{code}</div>
                    <p class="expires">⏱️ This code expires in 5 minutes</p>
                </div>
                
                <p><strong>How to use this code:</strong></p>
                <ol>
                    <li>Return to the login page</li>
                    <li>Enter this 6-digit code</li>
                    <li>Complete your sign in</li>
                </ol>
                
                <div class="warning-box">
                    <p style="margin: 0;"><strong>⚠️ Security Notice:</strong></p>
                    <p style="margin: 5px 0 0 0;">
                        If you didn't request this code, someone may be trying to access your account. 
                        Please ignore this email and consider changing your password.
                    </p>
                </div>
                
                <p style="margin-top: 30px; color: #6b7280; font-size: 14px;">
                    This is an automated message. Please do not reply to this email.
                </p>
                
                <div class="footer">
                    <p><strong>Ideation Axis Group</strong></p>
                    <p>Africa's Startup Engine</p>
                    <p style="margin-top: 15px;">
                        <a href="https://ideationaxis.com" style="color: #0A2463;">ideationaxis.com</a>
                    </p>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    
    try:
        # Send email using Microsoft Graph API
        result = await graph_client.send_email(
            to_emails=[email],
            subject="Your Axi Verification Code",
            body_html=html_content,
            department="noreply"  # Uses noreply@ideationaxis.com as reply-to
        )
        
        print(f"✅ [EMAIL] Sent OTP {code} to {email}")
        
        return {
            "success": True,
            "status": "sent",
            "email": email,
            "message": "OTP email sent successfully"
        }
        
    except Exception as e:
        print(f"❌ [EMAIL ERROR] Failed to send OTP to {email}: {e}")
        
        # Return error details
        return {
            "success": False,
            "status": "failed",
            "email": email,
            "error": str(e),
            "message": "Failed to send OTP email"
        }


async def send_welcome_email(email: str, name: str):
    """
    Send welcome email to new users after successful verification.
    
    Args:
        email: User email address
        name: User's name
    """
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: linear-gradient(135deg, #0A2463 0%, #1e40af 100%); color: white; padding: 30px; border-radius: 10px 10px 0 0; text-align: center; }}
            .content {{ background: #f9fafb; padding: 40px 30px; border-radius: 0 0 10px 10px; }}
            .cta-button {{ display: inline-block; padding: 15px 40px; background: #ffc007; color: #0A2463; text-decoration: none; border-radius: 6px; font-weight: bold; margin: 20px 0; }}
            .features {{ background: white; padding: 20px; border-radius: 8px; margin: 20px 0; }}
            .feature-item {{ margin: 15px 0; padding-left: 25px; position: relative; }}
            .feature-item:before {{ content: "✓"; position: absolute; left: 0; color: #10b981; font-weight: bold; }}
            .footer {{ text-align: center; margin-top: 30px; color: #6b7280; font-size: 12px; }}
            h1 {{ margin: 0; font-size: 28px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🎉 Welcome to Axi!</h1>
            </div>
            <div class="content">
                <p>Hi <strong>{name}</strong>,</p>
                <p>Welcome to <strong>Axi</strong> – where ideas transform into reality!</p>
                
                <div style="text-align: center;">
                    <a href="https://axi.ideationaxis.com/dashboard" class="cta-button">Go to Dashboard</a>
                </div>
                
                <p style="margin-top: 30px;">
                    <strong>Need help getting started?</strong><br>
                    reach out to our team anytime.
                </p>
                
                <div class="footer">
                    <p>Don't let your idea become another abandoned dream.</p>
                    <p><strong>The Axi Team</strong></p>
                    <p>Africa's Startup Engine</p>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    
    try:
        result = await graph_client.send_email(
            to_emails=[email],
            subject=f"🎉 Welcome to Axi Pipeline, {name}!",
            body_html=html_content,
            department="general"
        )
        
        print(f"✅ [EMAIL] Sent welcome email to {email}")
        return result
        
    except Exception as e:
        print(f"❌ [EMAIL ERROR] Failed to send welcome email to {email}: {e}")
        raise