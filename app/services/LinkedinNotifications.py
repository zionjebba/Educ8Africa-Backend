from sqlalchemy import and_, select
from app.models.linkedinpost import LinkedInPost
from app.models.notifications import Notification
from app.models.user import User
from app.services.MicrosoftGraphClient import MicrosoftGraphClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings

async def notify_employees_about_post(
    post_id: str,
    poster: User,
    linkedin_url: str,
    db: AsyncSession
):
    """
    Notify all employees about a new LinkedIn post.
    Sends both email and in-app notifications.
    """
    
    users_query = await db.execute(
        select(User).where(
            and_(
                User.is_active == True,
                User.user_id != poster.user_id
            )
        )
    )
    employees = users_query.scalars().all()
    
    # Create in-app notifications for all employees
    for employee in employees:
        notification = Notification(
            user_id=employee.user_id,
            title=f"{poster.first_name} shared a LinkedIn post!",
            message=f"{poster.first_name} {poster.last_name} just shared an update on LinkedIn. Show your support by liking and commenting!",
            type="linkedin_post",
            action_url=linkedin_url,
            action_label="View & Engage",
            reference_id=post_id
        )
        db.add(notification)
    
    await db.commit()
    
    # Send email notifications
    graph_client = MicrosoftGraphClient(
        tenant_id=settings.MICROSOFT_TENANT_ID,
        client_id=settings.MICROSOFT_CLIENT_ID,
        client_secret=settings.MICROSOFT_CLIENT_SECRET
    )
    
    email_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: linear-gradient(135deg, #0077b5 0%, #005885 100%); color: white; padding: 30px; border-radius: 10px 10px 0 0; text-align: center; }}
            .content {{ background: #f9fafb; padding: 30px; border-radius: 0 0 10px 10px; }}
            .post-box {{ background: white; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #0077b5; }}
            .cta-button {{ display: inline-block; padding: 12px 30px; background: #0077b5; color: white; text-decoration: none; border-radius: 6px; font-weight: bold; margin: 10px 5px; }}
            .points-badge {{ display: inline-block; padding: 8px 16px; background: #fbbf24; color: #78350f; border-radius: 20px; font-size: 14px; font-weight: bold; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1 style="margin: 0;">📣 New LinkedIn Post from {poster_name}!</h1>
            </div>
            <div class="content">
                <p>Hi <strong>{employee_name}</strong>,</p>
                <p>{poster_name} just shared an exciting update on LinkedIn!</p>
                
                <div class="post-box">
                    <p style="font-style: italic; color: #666;">"{post_preview}"</p>
                </div>
                
                <p><strong>🎯 Earn Culture Points!</strong></p>
                <ul>
                    <li><span class="points-badge">+5 Points</span> for liking the post</li>
                    <li><span class="points-badge">+10 Points</span> for commenting</li>
                </ul>
                
                <p>Show your support and help amplify our company's presence on LinkedIn!</p>
                
                <div style="text-align: center;">
                    <a href="{linkedin_url}" class="cta-button" target="_blank">View Post & Engage</a>
                </div>
                
                <p style="margin-top: 30px; color: #666; font-size: 12px;">
                    After engaging, don't forget to report your engagement on the dashboard to earn your culture points!
                </p>
            </div>
        </div>
    </body>
    </html>
    """
    
    # Get post content for preview
    post_query = await db.execute(
        select(LinkedInPost).where(LinkedInPost.post_id == post_id)
    )
    post = post_query.scalar_one()
    post_preview = post.post_content[:150] + "..." if len(post.post_content) > 150 else post.post_content
    
    # Send emails to all employees
    for employee in employees:
        try:
            await graph_client.send_email_with_template(
                from_email="culture@ideationaxis.com",
                to_emails=[employee.email],
                subject=f"🔗 {poster.first_name} shared on LinkedIn - Earn Culture Points!",
                template_html=email_template,
                template_vars={
                    "employee_name": employee.first_name,
                    "poster_name": f"{poster.first_name} {poster.last_name}",
                    "post_preview": post_preview,
                    "linkedin_url": linkedin_url
                }
            )
        except Exception as e:
            print(f"Failed to send email to {employee.email}: {e}")
    
    # Mark notifications and emails as sent
    post.notification_sent = True
    post.email_sent = True
    await db.commit()