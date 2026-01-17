from datetime import datetime
from typing import Dict, List, Optional
from app.models.user import User
from app.services.MicrosoftGraphClient import MicrosoftGraphClient


async def notify_match_created(
    user1: User,
    user2: User,
    meeting_link: str,
    match_date: datetime,
    graph_client: MicrosoftGraphClient
):
    """Send email notifications to matched users."""
    
    email_template = """
    <html>
    <body style="font-family: Arial, sans-serif; padding: 20px;">
        <h1 style="color: #3b82f6;">🎉 Social Sunday Match!</h1>
        <p>Hi {recipient_name},</p>
        <p>You've been matched with <strong>{partner_name}</strong> for Social Sunday on {date}!</p>
        
        <div style="background: #f3f4f6; padding: 15px; border-radius: 8px; margin: 20px 0;">
            <h3>Meeting Details:</h3>
            <p><strong>Partner:</strong> {partner_name} ({partner_department})</p>
            <p><strong>Date:</strong> {date}</p>
            <p><strong>Time:</strong> 10:00 AM - 11:00 AM</p>
        </div>
        
        <a href="{meeting_link}" 
           style="background: #3b82f6; color: white; padding: 12px 24px; 
                  text-decoration: none; border-radius: 6px; display: inline-block;">
            Join Teams Meeting
        </a>
        
        <p style="margin-top: 30px; color: #666;">
            Looking forward to helping you connect with your colleagues!
        </p>
    </body>
    </html>
    """
    
    # Send to user1
    try:
        await graph_client.send_email_with_template(
            from_email="info@ideationaxis.com",  # or your no-reply email
            to_emails=[user1.email],
            subject=f"Social Sunday Match - You're paired with {user2.first_name}!",
            template_html=email_template,
            template_vars={
                "recipient_name": user1.first_name,
                "partner_name": f"{user2.first_name} {user2.last_name}",
                "partner_department": user2.department.name if user2.department else "Unknown",
                "date": match_date.strftime("%B %d, %Y"),
                "meeting_link": meeting_link
            }
        )
        print(f"✅ Notification sent to {user1.email}")
    except Exception as e:
        print(f"⚠️ Failed to send email to {user1.email}: {e}")
    
    # Send to user2
    try:
        await graph_client.send_email_with_template(
            from_email="info@ideationaxis.com",
            to_emails=[user2.email],
            subject=f"Social Sunday Match - You're paired with {user1.first_name}!",
            template_html=email_template,
            template_vars={
                "recipient_name": user2.first_name,
                "partner_name": f"{user1.first_name} {user1.last_name}",
                "partner_department": user1.department.name if user1.department else "Unknown",
                "date": match_date.strftime("%B %d, %Y"),
                "meeting_link": meeting_link
            }
        )
        print(f"✅ Notification sent to {user2.email}")
    except Exception as e:
        print(f"⚠️ Failed to send email to {user2.email}: {e}")

async def notify_task_assigned(
    assigned_user: User,
    assigner: User,
    task_title: str,
    task_description: str,
    task_category: str,
    due_date: datetime,
    milestone_info: Optional[Dict] = None,
    app_url: str = "https://ideationaxis.com",
    graph_client: MicrosoftGraphClient = None
) -> Dict[str, str]:
    """
    Send email notification to a user when a task is assigned to them.
    
    Args:
        assigned_user: User who is being assigned the task
        assigner: User who is creating/assigning the task
        task_title: Title of the task
        task_description: Description of the task
        task_category: Category of the task (e.g., 'development', 'design')
        due_date: Task due date
        milestone_info: Optional milestone details dict with 'title', 'week_start', 'week_end'
        app_url: Frontend application URL for task dashboard link
        graph_client: Initialized MicrosoftGraphClient instance
    
    Returns:
        Dict with status information: {"status": "sent"/"failed", "email": user_email, "error": error_msg}
    """
    
    email_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: linear-gradient(135deg, #10b981 0%, #14b8a6 100%); color: white; padding: 30px; border-radius: 10px 10px 0 0; }}
            .content {{ background: #f9fafb; padding: 30px; border-radius: 0 0 10px 10px; }}
            .task-details {{ background: white; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #10b981; }}
            .task-title {{ font-size: 20px; font-weight: bold; color: #1f2937; margin-bottom: 10px; }}
            .detail-row {{ margin: 10px 0; }}
            .label {{ font-weight: bold; color: #6b7280; }}
            .value {{ color: #1f2937; }}
            .category-badge {{ display: inline-block; padding: 5px 15px; border-radius: 20px; font-size: 12px; font-weight: bold; color: white; background: #10b981; }}
            .footer {{ text-align: center; margin-top: 20px; color: #6b7280; font-size: 12px; }}
            .cta-button {{ display: inline-block; padding: 12px 30px; background: #10b981; color: white; text-decoration: none; border-radius: 6px; font-weight: bold; margin-top: 20px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1 style="margin: 0;">📋 New Task Assigned</h1>
            </div>
            <div class="content">
                <p>Hi <strong>{user_name}</strong>,</p>
                <p>You have been assigned a new task by <strong>{assigner_name}</strong>.</p>
                
                <div class="task-details">
                    <div class="task-title">{task_title}</div>
                    
                    <div class="detail-row">
                        <span class="label">Description:</span><br>
                        <span class="value">{task_description}</span>
                    </div>
                    
                    <div class="detail-row">
                        <span class="label">Category:</span><br>
                        <span class="category-badge">{task_category}</span>
                    </div>
                    
                    <div class="detail-row">
                        <span class="label">Due Date:</span><br>
                        <span class="value" style="color: #dc2626; font-weight: bold;">⏰ {due_date}</span>
                    </div>
                    
                    {milestone_section}
                </div>
                
                <p>Please review the task details and start working on it at your earliest convenience.</p>
                
                <div style="text-align: center;">
                    <a href="{app_url}/iaxos/dashboard" class="cta-button">View Task Dashboard</a>
                </div>
                
                <div class="footer">
                    <p>This is an automated notification from your Task Management System.</p>
                    <p>If you have any questions, please contact {assigner_name} at {assigner_email}</p>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    
    # Format due date
    due_date_formatted = due_date.strftime("%B %d, %Y at %I:%M %p")
    
    # Build milestone section if provided
    milestone_section = ""
    if milestone_info:
        milestone_section = f"""
        <div class="detail-row">
            <span class="label">Milestone:</span><br>
            <span class="value">{milestone_info.get('title', 'N/A')}</span><br>
            <span style="font-size: 12px; color: #6b7280;">
                Week: {milestone_info.get('week_start', '')[:10]} to {milestone_info.get('week_end', '')[:10]}
            </span>
        </div>
        """
    
    try:
        await graph_client.send_email_with_template(
            to_emails=[assigned_user.email],
            subject=f"New Task Assigned: {task_title}",
            template_html=email_template,
            template_vars={
                "user_name": f"{assigned_user.first_name} {assigned_user.last_name}",
                "assigner_name": f"{assigner.first_name} {assigner.last_name}",
                "assigner_email": assigner.email,
                "task_title": task_title,
                "task_description": task_description or "No description provided",
                "task_category": task_category.upper().replace('_', ' '),
                "due_date": due_date_formatted,
                "milestone_section": milestone_section,
                "app_url": app_url
            }
        )
        
        print(f"✅ Task notification sent to {assigned_user.email}")
        
        return {
            "status": "sent",
            "email": assigned_user.email,
            "user": f"{assigned_user.first_name} {assigned_user.last_name}"
        }
        
    except Exception as e:
        print(f"⚠️ Failed to send task notification to {assigned_user.email}: {e}")
        
        return {
            "status": "failed",
            "email": assigned_user.email,
            "user": f"{assigned_user.first_name} {assigned_user.last_name}",
            "error": str(e)
        }

async def notify_multiple_tasks_assigned(
    assigned_users: List[User],
    assigner: User,
    task_title: str,
    task_description: str,
    task_category: str,
    due_date: datetime,
    milestone_info: Optional[Dict] = None,
    app_url: str = "https://ideationaxis.com",
    graph_client: MicrosoftGraphClient = None
) -> List[Dict[str, str]]:
    """
    Send email notifications to multiple users when tasks are assigned.
    
    Args:
        assigned_users: List of users being assigned the task
        assigner: User who is creating/assigning the tasks
        task_title: Title of the task
        task_description: Description of the task
        task_category: Category of the task
        due_date: Task due date
        milestone_info: Optional milestone details
        app_url: Frontend application URL
        graph_client: Initialized MicrosoftGraphClient instance
    
    Returns:
        List of status dicts for each notification sent
    """
    
    results = []
    
    for user in assigned_users:
        result = await notify_task_assigned(
            assigned_user=user,
            assigner=assigner,
            task_title=task_title,
            task_description=task_description,
            task_category=task_category,
            due_date=due_date,
            milestone_info=milestone_info,
            app_url=app_url,
            graph_client=graph_client
        )
        results.append(result)
    
    return results

async def notify_task_under_review(
    assigned_user: User,
    reviewer: User,
    task_title: str,
    task_description: str,
    report_link: str,
    app_url: str = "https://ideationaxis.com",
    graph_client: MicrosoftGraphClient = None
) -> Dict[str, str]:
    """
    Send email notification when a task is set to 'under review' status.
    
    Args:
        assigned_user: User who submitted the task report
        reviewer: User who is reviewing the task
        task_title: Title of the task
        task_description: Description of the task
        report_link: Link to the submitted report document
        app_url: Frontend application URL
        graph_client: Initialized MicrosoftGraphClient instance
    
    Returns:
        Dict with status information
    """
    
    email_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%); color: white; padding: 30px; border-radius: 10px 10px 0 0; }}
            .content {{ background: #f9fafb; padding: 30px; border-radius: 0 0 10px 10px; }}
            .status-badge {{ display: inline-block; padding: 8px 20px; border-radius: 20px; font-size: 14px; font-weight: bold; color: white; background: #3b82f6; margin: 15px 0; }}
            .task-details {{ background: white; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #3b82f6; }}
            .task-title {{ font-size: 20px; font-weight: bold; color: #1f2937; margin-bottom: 10px; }}
            .detail-row {{ margin: 10px 0; }}
            .label {{ font-weight: bold; color: #6b7280; }}
            .value {{ color: #1f2937; }}
            .info-box {{ background: #dbeafe; border-left: 4px solid #3b82f6; padding: 15px; border-radius: 6px; margin: 20px 0; }}
            .footer {{ text-align: center; margin-top: 20px; color: #6b7280; font-size: 12px; }}
            .cta-button {{ display: inline-block; padding: 12px 30px; background: #3b82f6; color: white; text-decoration: none; border-radius: 6px; font-weight: bold; margin: 10px 5px; }}
            .secondary-button {{ display: inline-block; padding: 12px 30px; background: #10b981; color: white; text-decoration: none; border-radius: 6px; font-weight: bold; margin: 10px 5px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1 style="margin: 0;">🔍 Task Under Review</h1>
            </div>
            <div class="content">
                <p>Hi <strong>{user_name}</strong>,</p>
                <p>Great news! Your task has been set to <span class="status-badge">UNDER REVIEW</span></p>
                
                <div class="task-details">
                    <div class="task-title">{task_title}</div>
                    
                    <div class="detail-row">
                        <span class="label">Description:</span><br>
                        <span class="value">{task_description}</span>
                    </div>
                    
                    <div class="detail-row">
                        <span class="label">Reviewer:</span><br>
                        <span class="value">{reviewer_name}</span>
                    </div>
                </div>
                
                <div class="info-box">
                    <p style="margin: 0; color: #1e40af;">
                        <strong>📝 What's Next?</strong><br>
                        {reviewer_name} is now reviewing your submitted report. You'll receive another notification once the review is complete with feedback.
                    </p>
                </div>
                
                <div style="text-align: center;">
                    <a href="{report_link}" class="secondary-button" target="_blank">View Your Report</a>
                    <a href="{app_url}/iaxos/dashboard" class="cta-button">View Task Dashboard</a>
                </div>
                
                <div class="footer">
                    <p>This is an automated notification from your Task Management System.</p>
                    <p>You will be notified once {reviewer_name} completes the review.</p>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    
    try:
        await graph_client.send_email_with_template(
            from_email=reviewer.email,
            to_emails=[assigned_user.email],
            subject=f"Task Under Review: {task_title}",
            template_html=email_template,
            template_vars={
                "user_name": f"{assigned_user.first_name} {assigned_user.last_name}",
                "reviewer_name": f"{reviewer.first_name} {reviewer.last_name}",
                "task_title": task_title,
                "task_description": task_description or "No description provided",
                "report_link": report_link,
                "app_url": app_url
            }
        )
        
        print(f"✅ Under review notification sent to {assigned_user.email}")
        
        return {
            "status": "sent",
            "email": assigned_user.email,
            "user": f"{assigned_user.first_name} {assigned_user.last_name}"
        }
        
    except Exception as e:
        print(f"⚠️ Failed to send under review notification to {assigned_user.email}: {e}")
        
        return {
            "status": "failed",
            "email": assigned_user.email,
            "user": f"{assigned_user.first_name} {assigned_user.last_name}",
            "error": str(e)
        }
    
async def notify_report_submitted(
    submitter: User,
    reviewer: User,
    task_title: str,
    task_description: str,
    report_link: str,
    report_notes: str,
    app_url: str = "https://ideationaxis.com",
    graph_client: MicrosoftGraphClient = None
) -> Dict[str, str]:
    """
    Send email notification to reviewer when a team member submits a report.
    
    Args:
        submitter: User who submitted the report
        reviewer: User who needs to review the report (team lead/manager)
        task_title: Title of the task
        task_description: Description of the task
        report_link: Link to the submitted report document
        report_notes: Notes provided by the submitter
        app_url: Frontend application URL
        graph_client: Initialized MicrosoftGraphClient instance
    
    Returns:
        Dict with status information
    """
    
    email_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%); color: white; padding: 30px; border-radius: 10px 10px 0 0; }}
            .content {{ background: #f9fafb; padding: 30px; border-radius: 0 0 10px 10px; }}
            .status-badge {{ display: inline-block; padding: 8px 20px; border-radius: 20px; font-size: 14px; font-weight: bold; color: white; background: #f59e0b; margin: 15px 0; }}
            .task-details {{ background: white; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #f59e0b; }}
            .task-title {{ font-size: 20px; font-weight: bold; color: #1f2937; margin-bottom: 10px; }}
            .detail-row {{ margin: 10px 0; }}
            .label {{ font-weight: bold; color: #6b7280; }}
            .value {{ color: #1f2937; }}
            .info-box {{ background: #fef3c7; border-left: 4px solid #f59e0b; padding: 15px; border-radius: 6px; margin: 20px 0; }}
            .footer {{ text-align: center; margin-top: 20px; color: #6b7280; font-size: 12px; }}
            .cta-button {{ display: inline-block; padding: 12px 30px; background: #f59e0b; color: white; text-decoration: none; border-radius: 6px; font-weight: bold; margin: 10px 5px; }}
            .secondary-button {{ display: inline-block; padding: 12px 30px; background: #10b981; color: white; text-decoration: none; border-radius: 6px; font-weight: bold; margin: 10px 5px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1 style="margin: 0;">📄 New Report Submitted</h1>
            </div>
            <div class="content">
                <p>Hi <strong>{reviewer_name}</strong>,</p>
                <p><strong>{submitter_name}</strong> has submitted a report for review.</p>
                
                <div class="status-badge">AWAITING YOUR REVIEW</div>
                
                <div class="task-details">
                    <div class="task-title">{task_title}</div>
                    
                    <div class="detail-row">
                        <span class="label">Task Description:</span><br>
                        <span class="value">{task_description}</span>
                    </div>
                    
                    <div class="detail-row">
                        <span class="label">Submitted By:</span><br>
                        <span class="value">{submitter_name} ({submitter_email})</span>
                    </div>
                    
                    {notes_section}
                </div>
                
                <div class="info-box">
                    <p style="margin: 0; color: #92400e;">
                        <strong>⏰ Action Required</strong><br>
                        Please review the submitted report and provide feedback. You can set the task to "Under Review" and then approve or reject it.
                    </p>
                </div>
                
                <div style="text-align: center;">
                    <a href="{report_link}" class="secondary-button" target="_blank">View Report Document</a>
                    <a href="{app_url}/iaxos/reviews" class="cta-button">Review Now</a>
                </div>
                
                <div class="footer">
                    <p>This is an automated notification from your Task Management System.</p>
                    <p>Please review this report at your earliest convenience.</p>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    
    # Build notes section if provided
    notes_section = ""
    if report_notes and report_notes.strip():
        notes_section = f"""
        <div class="detail-row">
            <span class="label">Submitter's Notes:</span><br>
            <div style="background: #f3f4f6; padding: 10px; border-radius: 6px; margin-top: 5px;">
                <span class="value" style="font-style: italic;">{report_notes}</span>
            </div>
        </div>
        """
    
    try:
        await graph_client.send_email_with_template(
            from_email=submitter.email,
            to_emails=[reviewer.email],
            subject=f"Report Submitted for Review: {task_title}",
            template_html=email_template,
            template_vars={
                "reviewer_name": f"{reviewer.first_name} {reviewer.last_name}",
                "submitter_name": f"{submitter.first_name} {submitter.last_name}",
                "submitter_email": submitter.email,
                "task_title": task_title,
                "task_description": task_description or "No description provided",
                "notes_section": notes_section,
                "report_link": report_link,
                "app_url": app_url
            }
        )
        
        print(f"✅ Report submission notification sent to {reviewer.email}")
        
        return {
            "status": "sent",
            "email": reviewer.email,
            "reviewer": f"{reviewer.first_name} {reviewer.last_name}"
        }
        
    except Exception as e:
        print(f"⚠️ Failed to send report submission notification to {reviewer.email}: {e}")
        
        return {
            "status": "failed",
            "email": reviewer.email,
            "reviewer": f"{reviewer.first_name} {reviewer.last_name}",
            "error": str(e)
        }
    
async def notify_report_reviewed(
    submitter: User,
    reviewer: User,
    task_title: str,
    task_description: str,
    review_status: str,
    review_notes: str = None,
    points_awarded: int = 0,
    app_url: str = "https://ideationaxis.com",
    graph_client: MicrosoftGraphClient = None
) -> Dict[str, str]:
    """
    Send email notification to submitter after their report has been reviewed.
    
    Args:
        submitter: User who submitted the report
        reviewer: User who reviewed the report
        task_title: Title of the task
        task_description: Description of the task
        review_status: 'approved' or 'rejected'
        review_notes: Feedback notes from the reviewer
        points_awarded: Points awarded to the submitter (if approved)
        app_url: Frontend application URL
        graph_client: Initialized MicrosoftGraphClient instance
    
    Returns:
        Dict with status information
    """
    
    # Different templates for approved vs rejected
    if review_status == "approved":
        email_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #10b981 0%, #059669 100%); color: white; padding: 30px; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f9fafb; padding: 30px; border-radius: 0 0 10px 10px; }}
                .status-badge {{ display: inline-block; padding: 8px 20px; border-radius: 20px; font-size: 14px; font-weight: bold; color: white; background: #10b981; margin: 15px 0; }}
                .task-details {{ background: white; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #10b981; }}
                .task-title {{ font-size: 20px; font-weight: bold; color: #1f2937; margin-bottom: 10px; }}
                .detail-row {{ margin: 10px 0; }}
                .label {{ font-weight: bold; color: #6b7280; }}
                .value {{ color: #1f2937; }}
                .success-box {{ background: #d1fae5; border-left: 4px solid #10b981; padding: 15px; border-radius: 6px; margin: 20px 0; }}
                .points-badge {{ display: inline-block; padding: 10px 20px; background: #fbbf24; color: #78350f; border-radius: 25px; font-size: 18px; font-weight: bold; margin: 10px 0; }}
                .footer {{ text-align: center; margin-top: 20px; color: #6b7280; font-size: 12px; }}
                .cta-button {{ display: inline-block; padding: 12px 30px; background: #10b981; color: white; text-decoration: none; border-radius: 6px; font-weight: bold; margin: 10px 5px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1 style="margin: 0;">✅ Report Approved!</h1>
                </div>
                <div class="content">
                    <p>Hi <strong>{submitter_name}</strong>,</p>
                    <p>Great news! Your report has been <span class="status-badge">APPROVED</span> by {reviewer_name}.</p>
                    
                    <div class="task-details">
                        <div class="task-title">{task_title}</div>
                        
                        <div class="detail-row">
                            <span class="label">Task Description:</span><br>
                            <span class="value">{task_description}</span>
                        </div>
                        
                        <div class="detail-row">
                            <span class="label">Reviewed By:</span><br>
                            <span class="value">{reviewer_name}</span>
                        </div>
                        
                        {review_notes_section}
                    </div>
                    
                    <div class="success-box">
                        <p style="margin: 0; color: #065f46;">
                            <strong>🎉 Congratulations!</strong><br>
                            Your task has been marked as complete. Excellent work!
                        </p>
                        {points_section}
                    </div>
                    
                    <div style="text-align: center;">
                        <a href="{app_url}/iaxos/dashboard" class="cta-button">View Dashboard</a>
                    </div>
                    
                    <div class="footer">
                        <p>Keep up the great work! 🚀</p>
                        <p>This is an automated notification from your Task Management System.</p>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
        subject = f"✅ Report Approved: {task_title}"
    else:  # rejected
        email_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%); color: white; padding: 30px; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f9fafb; padding: 30px; border-radius: 0 0 10px 10px; }}
                .status-badge {{ display: inline-block; padding: 8px 20px; border-radius: 20px; font-size: 14px; font-weight: bold; color: white; background: #ef4444; margin: 15px 0; }}
                .task-details {{ background: white; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #ef4444; }}
                .task-title {{ font-size: 20px; font-weight: bold; color: #1f2937; margin-bottom: 10px; }}
                .detail-row {{ margin: 10px 0; }}
                .label {{ font-weight: bold; color: #6b7280; }}
                .value {{ color: #1f2937; }}
                .feedback-box {{ background: #fee2e2; border-left: 4px solid #ef4444; padding: 15px; border-radius: 6px; margin: 20px 0; }}
                .footer {{ text-align: center; margin-top: 20px; color: #6b7280; font-size: 12px; }}
                .cta-button {{ display: inline-block; padding: 12px 30px; background: #3b82f6; color: white; text-decoration: none; border-radius: 6px; font-weight: bold; margin: 10px 5px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1 style="margin: 0;">📋 Report Needs Revision</h1>
                </div>
                <div class="content">
                    <p>Hi <strong>{submitter_name}</strong>,</p>
                    <p>Your report has been reviewed by {reviewer_name} and requires some revisions.</p>
                    
                    <div class="status-badge">REVISION NEEDED</div>
                    
                    <div class="task-details">
                        <div class="task-title">{task_title}</div>
                        
                        <div class="detail-row">
                            <span class="label">Task Description:</span><br>
                            <span class="value">{task_description}</span>
                        </div>
                        
                        <div class="detail-row">
                            <span class="label">Reviewed By:</span><br>
                            <span class="value">{reviewer_name}</span>
                        </div>
                    </div>
                    
                    <div class="feedback-box">
                        <p style="margin: 0 0 10px 0; color: #991b1b;">
                            <strong>📝 Reviewer's Feedback:</strong>
                        </p>
                        <div style="background: white; padding: 12px; border-radius: 6px;">
                            <span style="color: #1f2937;">{review_feedback}</span>
                        </div>
                    </div>
                    
                    <p>Please review the feedback above, make the necessary changes, and resubmit your report.</p>
                    
                    <div style="text-align: center;">
                        <a href="{app_url}/iaxos/dashboard" class="cta-button">Update & Resubmit</a>
                    </div>
                    
                    <div class="footer">
                        <p>Don't worry - this is an opportunity to improve! 💪</p>
                        <p>This is an automated notification from your Task Management System.</p>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
        subject = f"📋 Report Needs Revision: {task_title}"
    
    # Build review notes section for approved reports
    review_notes_section = ""
    if review_status == "approved" and review_notes and review_notes.strip():
        review_notes_section = f"""
        <div class="detail-row">
            <span class="label">Reviewer's Comments:</span><br>
            <div style="background: #f3f4f6; padding: 10px; border-radius: 6px; margin-top: 5px;">
                <span class="value" style="font-style: italic;">{review_notes}</span>
            </div>
        </div>
        """
    
    # Build points section for approved reports
    points_section = ""
    if review_status == "approved" and points_awarded > 0:
        points_section = f"""
        <div style="text-align: center; margin-top: 15px;">
            <div class="points-badge">⭐ +{points_awarded} Points Earned!</div>
        </div>
        """
    
    try:
        await graph_client.send_email_with_template(
            from_email=reviewer.email,
            to_emails=[submitter.email],
            subject=subject,
            template_html=email_template,
            template_vars={
                "submitter_name": f"{submitter.first_name} {submitter.last_name}",
                "reviewer_name": f"{reviewer.first_name} {reviewer.last_name}",
                "task_title": task_title,
                "task_description": task_description or "No description provided",
                "review_notes_section": review_notes_section,
                "review_feedback": review_notes or "No specific feedback provided",
                "points_section": points_section,
                "app_url": app_url
            }
        )
        
        print(f"✅ Review notification ({review_status}) sent to {submitter.email}")
        
        return {
            "status": "sent",
            "email": submitter.email,
            "submitter": f"{submitter.first_name} {submitter.last_name}",
            "review_status": review_status
        }
        
    except Exception as e:
        print(f"⚠️ Failed to send review notification to {submitter.email}: {e}")
        
        return {
            "status": "failed",
            "email": submitter.email,
            "submitter": f"{submitter.first_name} {submitter.last_name}",
            "review_status": review_status,
            "error": str(e)
        }
    
async def notify_leadership_report_submitted(
    submitter: User,
    reviewer: User,
    report_title: str,
    report_period: str,
    document_link: str,
    report_notes: str = None,
    task_title: str = None,
    submitter_role: str = None,
    app_url: str = "https://ideationaxis.com",
    graph_client: MicrosoftGraphClient = None
) -> Dict[str, str]:
    """
    Send email notification to reviewer when a leadership report is submitted.
    
    Args:
        submitter: User who submitted the leadership report (team lead/dept head/senior mgmt)
        reviewer: User who needs to review the report (dept head/CEO)
        report_title: Title of the leadership report
        report_period: Reporting period (e.g., "January 2025", "Q1 2025")
        document_link: Link to the submitted report document
        report_notes: Additional notes from the submitter
        task_title: Associated task title (if any)
        submitter_role: Role of submitter (team_lead, department_head, etc.)
        app_url: Frontend application URL
        graph_client: Initialized MicrosoftGraphClient instance
    
    Returns:
        Dict with status information
    """
    
    # Determine role display name
    role_display = {
        "team_lead": "Team Lead",
        "department_head": "Department Head",
        "project_manager": "Project Manager",
        "ceo": "CEO",
        "coo": "COO",
        "cto": "CTO"
    }.get(submitter_role, "Leadership")
    
    email_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%); color: white; padding: 30px; border-radius: 10px 10px 0 0; }}
            .content {{ background: #f9fafb; padding: 30px; border-radius: 0 0 10px 10px; }}
            .status-badge {{ display: inline-block; padding: 8px 20px; border-radius: 20px; font-size: 14px; font-weight: bold; color: white; background: #8b5cf6; margin: 15px 0; }}
            .report-details {{ background: white; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #6366f1; }}
            .report-title {{ font-size: 20px; font-weight: bold; color: #1f2937; margin-bottom: 10px; }}
            .detail-row {{ margin: 10px 0; }}
            .label {{ font-weight: bold; color: #6b7280; }}
            .value {{ color: #1f2937; }}
            .role-badge {{ display: inline-block; padding: 5px 15px; border-radius: 15px; font-size: 12px; font-weight: bold; color: white; background: #6366f1; }}
            .info-box {{ background: #e0e7ff; border-left: 4px solid #6366f1; padding: 15px; border-radius: 6px; margin: 20px 0; }}
            .footer {{ text-align: center; margin-top: 20px; color: #6b7280; font-size: 12px; }}
            .cta-button {{ display: inline-block; padding: 12px 30px; background: #6366f1; color: white; text-decoration: none; border-radius: 6px; font-weight: bold; margin: 10px 5px; }}
            .secondary-button {{ display: inline-block; padding: 12px 30px; background: #10b981; color: white; text-decoration: none; border-radius: 6px; font-weight: bold; margin: 10px 5px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1 style="margin: 0;">📊 New Leadership Report Submitted</h1>
            </div>
            <div class="content">
                <p>Hi <strong>{reviewer_name}</strong>,</p>
                <p>A new leadership report has been submitted for your review.</p>
                
                <div class="status-badge">AWAITING YOUR REVIEW</div>
                
                <div class="report-details">
                    <div class="report-title">{report_title}</div>
                    
                    <div class="detail-row">
                        <span class="label">Submitted By:</span><br>
                        <span class="value">{submitter_name}</span>
                        <span class="role-badge">{submitter_role}</span>
                    </div>
                    
                    <div class="detail-row">
                        <span class="label">Email:</span><br>
                        <span class="value">{submitter_email}</span>
                    </div>
                    
                    <div class="detail-row">
                        <span class="label">Report Period:</span><br>
                        <span class="value">📅 {report_period}</span>
                    </div>
                    
                    {task_section}
                    
                    {notes_section}
                </div>
                
                <div class="info-box">
                    <p style="margin: 0; color: #3730a3;">
                        <strong>⏰ Action Required</strong><br>
                        Please review this leadership report and provide your feedback. This report requires your approval before the associated tasks can be marked as complete.
                    </p>
                </div>
                
                <div style="text-align: center;">
                    <a href="{document_link}" class="secondary-button" target="_blank">View Report Document</a>
                    <a href="{app_url}/iaxos/reviews" class="cta-button">Review Now</a>
                </div>
                
                <div class="footer">
                    <p>This is an automated notification from your Task Management System.</p>
                    <p>Please review this leadership report at your earliest convenience.</p>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    
    # Build task section if task is associated
    task_section = ""
    if task_title:
        task_section = f"""
        <div class="detail-row">
            <span class="label">Associated Task:</span><br>
            <span class="value">{task_title}</span>
        </div>
        """
    
    # Build notes section if provided
    notes_section = ""
    if report_notes and report_notes.strip():
        notes_section = f"""
        <div class="detail-row">
            <span class="label">Submitter's Notes:</span><br>
            <div style="background: #f3f4f6; padding: 10px; border-radius: 6px; margin-top: 5px;">
                <span class="value" style="font-style: italic;">{report_notes}</span>
            </div>
        </div>
        """
    
    try:
        await graph_client.send_email_with_template(
            from_email=submitter.email,
            to_emails=[reviewer.email],
            subject=f"Leadership Report Submitted for Review: {report_title}",
            template_html=email_template,
            template_vars={
                "reviewer_name": f"{reviewer.first_name} {reviewer.last_name}",
                "submitter_name": f"{submitter.first_name} {submitter.last_name}",
                "submitter_email": submitter.email,
                "submitter_role": role_display,
                "report_title": report_title,
                "report_period": report_period or "Not specified",
                "task_section": task_section,
                "notes_section": notes_section,
                "document_link": document_link,
                "app_url": app_url
            }
        )
        
        print(f"✅ Leadership report notification sent to {reviewer.email}")
        
        return {
            "status": "sent",
            "email": reviewer.email,
            "reviewer": f"{reviewer.first_name} {reviewer.last_name}"
        }
        
    except Exception as e:
        print(f"⚠️ Failed to send leadership report notification to {reviewer.email}: {e}")
        
        return {
            "status": "failed",
            "email": reviewer.email,
            "reviewer": f"{reviewer.first_name} {reviewer.last_name}",
            "error": str(e)
        }
    
async def notify_leadership_report_reviewed(
    submitter: User,
    reviewer: User,
    report_title: str,
    report_period: str,
    review_status: str,  # 'approved' or 'rejected'
    review_notes: str = None,
    points_awarded: int = 0,
    task_title: str = None,
    task_completed: bool = False,
    submitter_role: str = None,
    app_url: str = "https://ideationaxis.com",
    graph_client: MicrosoftGraphClient = None
) -> Dict[str, str]:
    """
    Send email notification to submitter after their leadership report has been reviewed.
    
    Args:
        submitter: User who submitted the leadership report
        reviewer: User who reviewed the report
        report_title: Title of the leadership report
        report_period: Reporting period
        review_status: 'approved' or 'rejected'
        review_notes: Feedback notes from the reviewer
        points_awarded: Points awarded to the submitter (if approved)
        task_title: Associated task title (if any)
        task_completed: Whether the associated task was marked complete
        submitter_role: Role of submitter (for display)
        app_url: Frontend application URL
        graph_client: Initialized MicrosoftGraphClient instance
    
    Returns:
        Dict with status information
    """
    
    # Determine role display name
    role_display = {
        "team_lead": "Team Lead",
        "department_head": "Department Head",
        "project_manager": "Project Manager",
        "ceo": "CEO",
        "coo": "COO",
        "cto": "CTO"
    }.get(submitter_role, "Leadership")
    
    # Different templates for approved vs rejected
    if review_status == "approved":
        email_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #10b981 0%, #059669 100%); color: white; padding: 30px; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f9fafb; padding: 30px; border-radius: 0 0 10px 10px; }}
                .status-badge {{ display: inline-block; padding: 8px 20px; border-radius: 20px; font-size: 14px; font-weight: bold; color: white; background: #10b981; margin: 15px 0; }}
                .report-details {{ background: white; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #10b981; }}
                .report-title {{ font-size: 20px; font-weight: bold; color: #1f2937; margin-bottom: 10px; }}
                .detail-row {{ margin: 10px 0; }}
                .label {{ font-weight: bold; color: #6b7280; }}
                .value {{ color: #1f2937; }}
                .success-box {{ background: #d1fae5; border-left: 4px solid #10b981; padding: 15px; border-radius: 6px; margin: 20px 0; }}
                .points-badge {{ display: inline-block; padding: 10px 20px; background: #fbbf24; color: #78350f; border-radius: 25px; font-size: 18px; font-weight: bold; margin: 10px 0; }}
                .role-badge {{ display: inline-block; padding: 5px 15px; border-radius: 15px; font-size: 12px; font-weight: bold; color: white; background: #6366f1; }}
                .footer {{ text-align: center; margin-top: 20px; color: #6b7280; font-size: 12px; }}
                .cta-button {{ display: inline-block; padding: 12px 30px; background: #10b981; color: white; text-decoration: none; border-radius: 6px; font-weight: bold; margin: 10px 5px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1 style="margin: 0;">✅ Leadership Report Approved!</h1>
                </div>
                <div class="content">
                    <p>Hi <strong>{submitter_name}</strong>,</p>
                    <p>Excellent work! Your leadership report has been <span class="status-badge">APPROVED</span> by {reviewer_name}.</p>
                    
                    <div class="report-details">
                        <div class="report-title">{report_title}</div>
                        
                        <div class="detail-row">
                            <span class="label">Your Role:</span><br>
                            <span class="role-badge">{submitter_role}</span>
                        </div>
                        
                        <div class="detail-row">
                            <span class="label">Report Period:</span><br>
                            <span class="value">📅 {report_period}</span>
                        </div>
                        
                        <div class="detail-row">
                            <span class="label">Reviewed By:</span><br>
                            <span class="value">{reviewer_name}</span>
                        </div>
                        
                        {task_section}
                        
                        {review_notes_section}
                    </div>
                    
                    <div class="success-box">
                        <p style="margin: 0; color: #065f46;">
                            <strong>🎉 Outstanding Leadership!</strong><br>
                            Your report demonstrates excellent {submitter_role_lower} performance. {task_status_message}
                        </p>
                        {points_section}
                    </div>
                    
                    <div style="text-align: center;">
                        <a href="{app_url}/iaxos/dashboard" class="cta-button">View Dashboard</a>
                    </div>
                    
                    <div class="footer">
                        <p>Keep up the exceptional leadership! 🚀</p>
                        <p>This is an automated notification from your Task Management System.</p>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
        subject = f"✅ Leadership Report Approved: {report_title}"
    else:  # rejected
        email_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%); color: white; padding: 30px; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f9fafb; padding: 30px; border-radius: 0 0 10px 10px; }}
                .status-badge {{ display: inline-block; padding: 8px 20px; border-radius: 20px; font-size: 14px; font-weight: bold; color: white; background: #ef4444; margin: 15px 0; }}
                .report-details {{ background: white; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #ef4444; }}
                .report-title {{ font-size: 20px; font-weight: bold; color: #1f2937; margin-bottom: 10px; }}
                .detail-row {{ margin: 10px 0; }}
                .label {{ font-weight: bold; color: #6b7280; }}
                .value {{ color: #1f2937; }}
                .feedback-box {{ background: #fee2e2; border-left: 4px solid #ef4444; padding: 15px; border-radius: 6px; margin: 20px 0; }}
                .role-badge {{ display: inline-block; padding: 5px 15px; border-radius: 15px; font-size: 12px; font-weight: bold; color: white; background: #6366f1; }}
                .footer {{ text-align: center; margin-top: 20px; color: #6b7280; font-size: 12px; }}
                .cta-button {{ display: inline-block; padding: 12px 30px; background: #3b82f6; color: white; text-decoration: none; border-radius: 6px; font-weight: bold; margin: 10px 5px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1 style="margin: 0;">📋 Leadership Report Needs Revision</h1>
                </div>
                <div class="content">
                    <p>Hi <strong>{submitter_name}</strong>,</p>
                    <p>Your leadership report has been reviewed by {reviewer_name} and requires some revisions.</p>
                    
                    <div class="status-badge">REVISION NEEDED</div>
                    
                    <div class="report-details">
                        <div class="report-title">{report_title}</div>
                        
                        <div class="detail-row">
                            <span class="label">Your Role:</span><br>
                            <span class="role-badge">{submitter_role}</span>
                        </div>
                        
                        <div class="detail-row">
                            <span class="label">Report Period:</span><br>
                            <span class="value">📅 {report_period}</span>
                        </div>
                        
                        <div class="detail-row">
                            <span class="label">Reviewed By:</span><br>
                            <span class="value">{reviewer_name}</span>
                        </div>
                        
                        {task_section}
                    </div>
                    
                    <div class="feedback-box">
                        <p style="margin: 0 0 10px 0; color: #991b1b;">
                            <strong>📝 Reviewer's Feedback:</strong>
                        </p>
                        <div style="background: white; padding: 12px; border-radius: 6px;">
                            <span style="color: #1f2937;">{review_feedback}</span>
                        </div>
                    </div>
                    
                    <p>Please review the feedback above, address the concerns raised, and resubmit your leadership report.</p>
                    
                    <div style="text-align: center;">
                        <a href="{app_url}/iaxos/dashboard" class="cta-button">Update & Resubmit</a>
                    </div>
                    
                    <div class="footer">
                        <p>This is an opportunity to strengthen your leadership reporting! 💪</p>
                        <p>This is an automated notification from your Task Management System.</p>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
        subject = f"📋 Leadership Report Needs Revision: {report_title}"
    
    # Build task section
    task_section = ""
    if task_title:
        task_status_text = "marked as complete" if task_completed else "associated with this report"
        task_section = f"""
        <div class="detail-row">
            <span class="label">Associated Task:</span><br>
            <span class="value">{task_title}</span>
            {" ✅" if task_completed else ""}
        </div>
        """
    
    # Build review notes section for approved reports
    review_notes_section = ""
    if review_status == "approved" and review_notes and review_notes.strip():
        review_notes_section = f"""
        <div class="detail-row">
            <span class="label">Reviewer's Comments:</span><br>
            <div style="background: #f3f4f6; padding: 10px; border-radius: 6px; margin-top: 5px;">
                <span class="value" style="font-style: italic;">{review_notes}</span>
            </div>
        </div>
        """
    
    # Build points section for approved reports
    points_section = ""
    if review_status == "approved" and points_awarded > 0:
        points_section = f"""
        <div style="text-align: center; margin-top: 15px;">
            <div class="points-badge">⭐ +{points_awarded} Leadership Points Earned!</div>
        </div>
        """
    
    # Task status message
    task_status_message = ""
    if task_completed:
        task_status_message = "Your associated task has been marked as complete."
    elif task_title:
        task_status_message = "The associated task progress has been updated."
    
    try:
        await graph_client.send_email_with_template(
            from_email=reviewer.email,
            to_emails=[submitter.email],
            subject=subject,
            template_html=email_template,
            template_vars={
                "submitter_name": f"{submitter.first_name} {submitter.last_name}",
                "reviewer_name": f"{reviewer.first_name} {reviewer.last_name}",
                "submitter_role": role_display,
                "submitter_role_lower": role_display.lower(),
                "report_title": report_title,
                "report_period": report_period or "Not specified",
                "task_section": task_section,
                "review_notes_section": review_notes_section,
                "review_feedback": review_notes or "No specific feedback provided",
                "points_section": points_section,
                "task_status_message": task_status_message,
                "app_url": app_url
            }
        )
        
        print(f"✅ Leadership report review notification ({review_status}) sent to {submitter.email}")
        
        return {
            "status": "sent",
            "email": submitter.email,
            "submitter": f"{submitter.first_name} {submitter.last_name}",
            "review_status": review_status
        }
        
    except Exception as e:
        print(f"⚠️ Failed to send leadership report review notification to {submitter.email}: {e}")
        
        return {
            "status": "failed",
            "email": submitter.email,
            "submitter": f"{submitter.first_name} {submitter.last_name}",
            "review_status": review_status,
            "error": str(e)
        }