import base64
from datetime import datetime
import json

from app.constants.constants import ADMIN_EMAILS
from app.services.EventTicketGenerator import generate_ticket_pdf
from app.services.MicrosoftGraphClient import MicrosoftGraphClient
from app.services.MicrosoftGraphClientPublic import MicrosoftGraphClientPublic


async def notify_partnership_application_received(
    application_data: dict,
    graph_client: MicrosoftGraphClientPublic
) -> dict:
    """Send confirmation email for partnership application."""
    
    email_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%); color: white; padding: 30px; border-radius: 10px 10px 0 0; }}
            .content {{ background: #f9fafb; padding: 30px; border-radius: 0 0 10px 10px; }}
            .application-details {{ background: white; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #8b5cf6; }}
            .detail-row {{ margin: 10px 0; }}
            .label {{ font-weight: bold; color: #6b7280; }}
            .value {{ color: #1f2937; }}
            .status-badge {{ display: inline-block; padding: 8px 20px; border-radius: 20px; font-size: 14px; font-weight: bold; color: white; background: #10b981; margin: 15px 0; }}
            .footer {{ text-align: center; margin-top: 20px; color: #6b7280; font-size: 12px; }}
            .cta-button {{ display: inline-block; padding: 12px 30px; background: #8b5cf6; color: white; text-decoration: none; border-radius: 6px; font-weight: bold; margin-top: 20px; }}
            h1 {{ margin: 0; }}
            h3 {{ margin-top: 0; color: #7c3aed; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🤝 Partnership Application Received</h1>
            </div>
            <div class="content">
                <p>Hi <strong>{contact_person}</strong>,</p>
                <p>Thank you for submitting your partnership application to Ideation Axis Group!</p>
                
                <div class="status-badge">APPLICATION RECEIVED</div>
                
                <div class="application-details">
                    <h3>Application Summary</h3>
                    <div class="detail-row">
                        <span class="label">Organization:</span><br>
                        <span class="value">{organization_name}</span>
                    </div>
                    <div class="detail-row">
                        <span class="label">Application ID:</span><br>
                        <span class="value">{application_id}</span>
                    </div>
                    <div class="detail-row">
                        <span class="label">Organization Type:</span><br>
                        <span class="value">{organization_type}</span>
                    </div>
                    <div class="detail-row">
                        <span class="label">Submitted:</span><br>
                        <span class="value">{submission_date}</span>
                    </div>
                </div>
                
                <p><strong>What happens next?</strong></p>
                <ul>
                    <li>Our team will review your application within 3-5 business days</li>
                    <li>We'll contact you at {email} for any additional information</li>
                    <li>You'll receive a decision via email once the review is complete</li>
                </ul>
                
                <div style="text-align: center;">
                    <a href="https://ideationaxis.com" class="cta-button">Contact Us</a>
                </div>
                
                <div class="footer">
                    <p>Thank you for your interest in partnering with Ideation Axis Group!</p>
                    <p>Best regards,<br>The Ideation Axis Group Team</p>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    
    try:
        result = await graph_client.send_user_confirmation(
            to_email=application_data['email'],
            subject=f"Partnership Application Received - {application_data['organization_name']}",
            template_html=email_template,
            template_vars={
                "contact_person": application_data['contact_person_name'],
                "organization_name": application_data['organization_name'],
                "application_id": application_data['application_id'],
                "organization_type": application_data['organization_type'].replace('_', ' ').title(),
                "submission_date": application_data['submitted_at'].strftime("%B %d, %Y at %I:%M %p"),
                "email": application_data['email']
            },
            department="partnerships"
        )
        print(f"✅ Partnership confirmation sent to {application_data['email']}")
        return {"status": "sent", "email": application_data['email'], "type": "partnership_confirmation"}
    except Exception as e:
        print(f"⚠️ Failed to send partnership confirmation: {e}")
        return {"status": "failed", "email": application_data['email'], "type": "partnership_confirmation", "error": str(e)}


async def notify_admin_new_partnership_application(
    application_data: dict,
    graph_client: MicrosoftGraphClientPublic,
    admin_emails: list = ADMIN_EMAILS
) -> dict:
    """Notify admin team about new partnership application."""
    
    # Parse partnership types
    try:
        types_list = json.loads(application_data['partnership_types'])
        types_html = "".join([f'<span style="display:inline-block;padding:5px 12px;border-radius:15px;font-size:12px;font-weight:bold;color:white;background:#8b5cf6;margin:3px;">{t}</span>' for t in types_list])
    except:
        types_html = '<span>Not specified</span>'
    
    email_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%); color: white; padding: 30px; border-radius: 10px 10px 0 0; }}
            .content {{ background: #f9fafb; padding: 30px; border-radius: 0 0 10px 10px; }}
            .details {{ background: white; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #8b5cf6; }}
            .detail-row {{ margin: 12px 0; }}
            .label {{ font-weight: bold; color: #6b7280; font-size: 12px; text-transform: uppercase; }}
            .value {{ color: #1f2937; font-size: 15px; }}
            .priority-badge {{ display: inline-block; padding: 8px 20px; border-radius: 20px; font-size: 14px; font-weight: bold; color: white; background: #8b5cf6; }}
            .text-box {{ background: #f3f4f6; padding: 15px; border-radius: 8px; margin: 10px 0; }}
            h1 {{ margin: 0; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🤝 New Partnership Application</h1>
            </div>
            <div class="content">
                <div class="priority-badge">NEW APPLICATION</div>
                
                <div class="details">
                    <div class="detail-row">
                        <div class="label">Application ID</div>
                        <div class="value">{application_id}</div>
                    </div>
                    <div class="detail-row">
                        <div class="label">Organization</div>
                        <div class="value">{organization_name}</div>
                    </div>
                    <div class="detail-row">
                        <div class="label">Organization Type</div>
                        <div class="value">{organization_type}</div>
                    </div>
                    <div class="detail-row">
                        <div class="label">Contact Person</div>
                        <div class="value">{contact_person}</div>
                    </div>
                    <div class="detail-row">
                        <div class="label">Email</div>
                        <div class="value"><a href="mailto:{email}">{email}</a></div>
                    </div>
                    <div class="detail-row">
                        <div class="label">Phone</div>
                        <div class="value">{phone_number}</div>
                    </div>
                    <div class="detail-row">
                        <div class="label">LinkedIn/Website</div>
                        <div class="value">{linkedin_website}</div>
                    </div>
                    <div class="detail-row">
                        <div class="label">Partnership Types</div>
                        <div class="value">{partnership_types}</div>
                    </div>
                    <div class="detail-row">
                        <div class="label">Submitted</div>
                        <div class="value">{submission_date}</div>
                    </div>
                </div>
                
                <div class="text-box">
                    <div class="label">Value They Can Bring</div>
                    <p>{value_to_bring}</p>
                </div>
                
                <div class="text-box">
                    <div class="label">Value They Hope to Receive</div>
                    <p>{value_to_receive}</p>
                </div>
                
                <div class="text-box">
                    <div class="label">Referrer</div>
                    <p>{referrer}</p>
                </div>
                
                <p style="text-align:center;margin-top:20px;color:#6b7280;font-size:12px;">
                    💡 Click Reply to respond directly to the applicant
                </p>
            </div>
        </div>
    </body>
    </html>
    """
    
    try:
        result = await graph_client.send_admin_notification(
            admin_emails=admin_emails,
            subject=f"[Partnership] New Application - {application_data['organization_name']}",
            template_html=email_template,
            template_vars={
                "application_id": application_data['application_id'],
                "organization_name": application_data['organization_name'],
                "organization_type": application_data['organization_type'].replace('_', ' ').title(),
                "contact_person": application_data['contact_person_name'],
                "email": application_data['email'],
                "phone_number": application_data['phone_number'],
                "linkedin_website": application_data.get('linkedin_website') or 'Not provided',
                "partnership_types": types_html,
                "value_to_bring": application_data.get('value_to_bring') or 'Not provided',
                "value_to_receive": application_data.get('value_to_receive') or 'Not provided',
                "referrer": application_data.get('referrer') or 'Not provided',
                "submission_date": application_data['submitted_at'].strftime("%B %d, %Y at %I:%M %p")
            },
            reply_to_applicant=application_data['email']
        )
        print(f"✅ Admin notified about partnership application from {application_data['organization_name']}")
        return {"status": "sent", "type": "admin_partnership_notification"}
    except Exception as e:
        print(f"⚠️ Failed to send admin partnership notification: {e}")
        return {"status": "failed", "type": "admin_partnership_notification", "error": str(e)}


# ============================================================
# SPEAKER NOTIFICATIONS
# ============================================================

async def notify_speaker_application_received(
    application_data: dict,
    graph_client: MicrosoftGraphClientPublic
) -> dict:
    """Send confirmation email for speaker application."""
    
    email_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%); color: white; padding: 30px; border-radius: 10px 10px 0 0; }}
            .content {{ background: #f9fafb; padding: 30px; border-radius: 0 0 10px 10px; }}
            .application-details {{ background: white; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #f59e0b; }}
            .detail-row {{ margin: 10px 0; }}
            .label {{ font-weight: bold; color: #6b7280; }}
            .value {{ color: #1f2937; }}
            .status-badge {{ display: inline-block; padding: 8px 20px; border-radius: 20px; font-size: 14px; font-weight: bold; color: white; background: #10b981; margin: 15px 0; }}
            .topic-badge {{ display: inline-block; padding: 5px 15px; border-radius: 15px; font-size: 12px; font-weight: bold; color: white; background: #f59e0b; margin: 5px 5px 5px 0; }}
            .footer {{ text-align: center; margin-top: 20px; color: #6b7280; font-size: 12px; }}
            .cta-button {{ display: inline-block; padding: 12px 30px; background: #f59e0b; color: white; text-decoration: none; border-radius: 6px; font-weight: bold; margin-top: 20px; }}
            h1 {{ margin: 0; }}
            h3 {{ margin-top: 0; color: #d97706; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🎤 Speaker Application Received</h1>
            </div>
            <div class="content">
                <p>Hi <strong>{full_name}</strong>,</p>
                <p>Thank you for your interest in speaking at Ideation Axis Group events!</p>
                
                <div class="status-badge">APPLICATION UNDER REVIEW</div>
                
                <div class="application-details">
                    <h3>Your Speaking Proposal</h3>
                    <div class="detail-row">
                        <span class="label">Application ID:</span><br>
                        <span class="value">{application_id}</span>
                    </div>
                    <div class="detail-row">
                        <span class="label">Proposed Topic:</span><br>
                        <span class="topic-badge">{proposal_topic}</span>
                    </div>
                    <div class="detail-row">
                        <span class="label">Role/Organization:</span><br>
                        <span class="value">{role_organization}</span>
                    </div>
                    <div class="detail-row">
                        <span class="label">Country:</span><br>
                        <span class="value">📍 {country}</span>
                    </div>
                    <div class="detail-row">
                        <span class="label">Submitted:</span><br>
                        <span class="value">{submission_date}</span>
                    </div>
                </div>
                
                <p><strong>Next Steps:</strong></p>
                <ul>
                    <li>Our speaker selection committee will review your proposal</li>
                    <li>Review process typically takes 7-10 business days</li>
                    <li>We'll notify you via email about the selection decision</li>
                    <li>If selected, we'll coordinate on event details and scheduling</li>
                </ul>
                
                <div style="text-align: center;">
                    <a href="https://ideationaxis.com/events" class="cta-button">View Upcoming Events</a>
                </div>
                
                <div class="footer">
                    <p>We're excited to review your speaking proposal!</p>
                    <p>Best regards,<br>The Ideation Axis Group Events Team</p>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    
    try:
        result = await graph_client.send_user_confirmation(
            to_email=application_data['email'],
            subject=f"Speaker Application Received - {application_data['full_name']}",
            template_html=email_template,
            template_vars={
                "full_name": application_data['full_name'],
                "application_id": application_data['application_id'],
                "proposal_topic": application_data['proposal_topic'],
                "role_organization": application_data['role_organization'],
                "country": application_data['country'],
                "submission_date": application_data['submitted_at'].strftime("%B %d, %Y at %I:%M %p")
            },
            department="events"
        )
        print(f"✅ Speaker confirmation sent to {application_data['email']}")
        return {"status": "sent", "email": application_data['email'], "type": "speaker_confirmation"}
    except Exception as e:
        print(f"⚠️ Failed to send speaker confirmation: {e}")
        return {"status": "failed", "email": application_data['email'], "type": "speaker_confirmation", "error": str(e)}


async def notify_admin_new_speaker_application(
    application_data: dict,
    graph_client: MicrosoftGraphClientPublic,
    admin_emails: list = ADMIN_EMAILS
) -> dict:
    """Notify admin team about new speaker application."""
    
    # Parse speaking formats
    try:
        formats_list = json.loads(application_data['speaking_formats'])
        formats_html = "".join([f'<span style="display:inline-block;padding:5px 12px;border-radius:15px;font-size:12px;font-weight:bold;color:white;background:#f59e0b;margin:3px;">{f}</span>' for f in formats_list])
    except:
        formats_html = '<span>Not specified</span>'
    
    email_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%); color: white; padding: 30px; border-radius: 10px 10px 0 0; }}
            .content {{ background: #f9fafb; padding: 30px; border-radius: 0 0 10px 10px; }}
            .details {{ background: white; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #f59e0b; }}
            .detail-row {{ margin: 12px 0; }}
            .label {{ font-weight: bold; color: #6b7280; font-size: 12px; text-transform: uppercase; }}
            .value {{ color: #1f2937; font-size: 15px; }}
            .priority-badge {{ display: inline-block; padding: 8px 20px; border-radius: 20px; font-size: 14px; font-weight: bold; color: white; background: #f59e0b; }}
            .text-box {{ background: #fef3c7; padding: 15px; border-radius: 8px; margin: 10px 0; }}
            h1 {{ margin: 0; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🎤 New Speaker Application</h1>
            </div>
            <div class="content">
                <div class="priority-badge">NEW APPLICATION</div>
                
                <div class="details">
                    <div class="detail-row">
                        <div class="label">Application ID</div>
                        <div class="value">{application_id}</div>
                    </div>
                    <div class="detail-row">
                        <div class="label">Full Name</div>
                        <div class="value">{full_name}</div>
                    </div>
                    <div class="detail-row">
                        <div class="label">Email</div>
                        <div class="value"><a href="mailto:{email}">{email}</a></div>
                    </div>
                    <div class="detail-row">
                        <div class="label">Phone</div>
                        <div class="value">{phone_number}</div>
                    </div>
                    <div class="detail-row">
                        <div class="label">Role/Organization</div>
                        <div class="value">{role_organization}</div>
                    </div>
                    <div class="detail-row">
                        <div class="label">Country</div>
                        <div class="value">📍 {country}</div>
                    </div>
                    <div class="detail-row">
                        <div class="label">Proposed Topic</div>
                        <div class="value" style="font-weight:bold;color:#d97706;">{proposal_topic}</div>
                    </div>
                    <div class="detail-row">
                        <div class="label">Speaking Formats</div>
                        <div class="value">{speaking_formats}</div>
                    </div>
                    <div class="detail-row">
                        <div class="label">Submitted</div>
                        <div class="value">{submission_date}</div>
                    </div>
                </div>
                
                <div class="text-box">
                    <div class="label">Why They Want to Speak</div>
                    <p>{why_speak}</p>
                </div>
                
                <div class="text-box">
                    <div class="label">Short Bio</div>
                    <p>{short_bio}</p>
                </div>
                
                <div class="text-box">
                    <div class="label">Previous Engagements</div>
                    <p>{previous_engagements}</p>
                </div>
                
                <p style="text-align:center;margin-top:20px;color:#6b7280;font-size:12px;">
                    💡 Click Reply to respond directly to the applicant
                </p>
            </div>
        </div>
    </body>
    </html>
    """
    
    try:
        result = await graph_client.send_admin_notification(
            admin_emails=admin_emails,
            subject=f"[Speaker] New Application - {application_data['full_name']} | {application_data['proposal_topic']}",
            template_html=email_template,
            template_vars={
                "application_id": application_data['application_id'],
                "full_name": application_data['full_name'],
                "email": application_data['email'],
                "phone_number": application_data['phone_number'],
                "role_organization": application_data['role_organization'],
                "country": application_data['country'],
                "proposal_topic": application_data['proposal_topic'],
                "speaking_formats": formats_html,
                "why_speak": application_data['why_speak'],
                "short_bio": application_data['short_bio'],
                "previous_engagements": application_data.get('previous_engagements') or 'Not provided',
                "submission_date": application_data['submitted_at'].strftime("%B %d, %Y at %I:%M %p")
            },
            reply_to_applicant=application_data['email']
        )
        print(f"✅ Admin notified about speaker application from {application_data['full_name']}")
        return {"status": "sent", "type": "admin_speaker_notification"}
    except Exception as e:
        print(f"⚠️ Failed to send admin speaker notification: {e}")
        return {"status": "failed", "type": "admin_speaker_notification", "error": str(e)}
    

async def notify_sponsorship_application_received(
    application_data: dict,
    graph_client: MicrosoftGraphClientPublic
) -> dict:
    """Send confirmation email for sponsorship application."""
    
    # Parse sponsorship tiers
    try:
        tiers_list = json.loads(application_data['sponsorship_tiers'])
        tiers_html = "".join([f'<span class="tier-badge">{tier}</span>' for tier in tiers_list])
    except:
        tiers_html = '<span class="value">Not specified</span>'
    
    booth_interest = "Yes" if application_data.get('booth_interest') else "No"
    
    email_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%); color: white; padding: 30px; border-radius: 10px 10px 0 0; }}
            .content {{ background: #f9fafb; padding: 30px; border-radius: 0 0 10px 10px; }}
            .application-details {{ background: white; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #3b82f6; }}
            .detail-row {{ margin: 10px 0; }}
            .label {{ font-weight: bold; color: #6b7280; }}
            .value {{ color: #1f2937; }}
            .status-badge {{ display: inline-block; padding: 8px 20px; border-radius: 20px; font-size: 14px; font-weight: bold; color: white; background: #10b981; margin: 15px 0; }}
            .tier-badge {{ display: inline-block; padding: 5px 15px; border-radius: 15px; font-size: 12px; font-weight: bold; color: white; background: #3b82f6; margin: 5px 5px 5px 0; }}
            .footer {{ text-align: center; margin-top: 20px; color: #6b7280; font-size: 12px; }}
            .cta-button {{ display: inline-block; padding: 12px 30px; background: #3b82f6; color: white; text-decoration: none; border-radius: 6px; font-weight: bold; margin-top: 20px; }}
            h1 {{ margin: 0; }}
            h3 {{ margin-top: 0; color: #1d4ed8; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>💼 Sponsorship Application Received</h1>
            </div>
            <div class="content">
                <p>Hi <strong>{contact_person}</strong>,</p>
                <p>Thank you for your interest in sponsoring Ideation Axis Group events!</p>
                
                <div class="status-badge">APPLICATION RECEIVED</div>
                
                <div class="application-details">
                    <h3>Sponsorship Details</h3>
                    <div class="detail-row">
                        <span class="label">Organization:</span><br>
                        <span class="value">{organization_name}</span>
                    </div>
                    <div class="detail-row">
                        <span class="label">Application ID:</span><br>
                        <span class="value">{application_id}</span>
                    </div>
                    <div class="detail-row">
                        <span class="label">Industry:</span><br>
                        <span class="value">{industry}</span>
                    </div>
                    <div class="detail-row">
                        <span class="label">Interest in Tiers:</span><br>
                        {sponsorship_tiers}
                    </div>
                    <div class="detail-row">
                        <span class="label">Booth Interest:</span><br>
                        <span class="value">{booth_interest}</span>
                    </div>
                    <div class="detail-row">
                        <span class="label">Submitted:</span><br>
                        <span class="value">{submission_date}</span>
                    </div>
                </div>
                
                <p><strong>What to expect:</strong></p>
                <ul>
                    <li>Our sponsorship team will review your application within 5-7 business days</li>
                    <li>We'll contact you to discuss sponsorship opportunities in detail</li>
                    <li>You'll receive a customized sponsorship package based on your interests</li>
                </ul>
                
                <div style="text-align: center;">
                    <a href="https://ideationaxis.com/partners" class="cta-button">Learn More</a>
                </div>
                
                <div class="footer">
                    <p>We look forward to exploring sponsorship opportunities with you!</p>
                    <p>Best regards,<br>The Ideation Axis Group Sponsorship Team</p>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    
    try:
        result = await graph_client.send_user_confirmation(
            to_email=application_data['email'],
            subject=f"Sponsorship Application Received - {application_data['organization_name']}",
            template_html=email_template,
            template_vars={
                "contact_person": application_data['contact_person_name'],
                "organization_name": application_data['organization_name'],
                "application_id": application_data['application_id'],
                "industry": application_data['industry'],
                "sponsorship_tiers": tiers_html,
                "booth_interest": booth_interest,
                "submission_date": application_data['submitted_at'].strftime("%B %d, %Y at %I:%M %p")
            },
            department="sponsorship"
        )
        print(f"✅ Sponsorship confirmation sent to {application_data['email']}")
        return {"status": "sent", "email": application_data['email'], "type": "sponsorship_confirmation"}
    except Exception as e:
        print(f"⚠️ Failed to send sponsorship confirmation: {e}")
        return {"status": "failed", "email": application_data['email'], "type": "sponsorship_confirmation", "error": str(e)}


async def notify_admin_new_sponsorship_application(
    application_data: dict,
    graph_client: MicrosoftGraphClientPublic,
    admin_emails: list = ADMIN_EMAILS
) -> dict:
    """Notify admin team about new sponsorship application."""
    
    # Parse sponsorship tiers
    try:
        tiers_list = json.loads(application_data['sponsorship_tiers'])
        tiers_html = "".join([f'<span style="display:inline-block;padding:5px 12px;border-radius:15px;font-size:12px;font-weight:bold;color:white;background:#3b82f6;margin:3px;">{t}</span>' for t in tiers_list])
    except:
        tiers_html = '<span>Not specified</span>'
    
    email_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%); color: white; padding: 30px; border-radius: 10px 10px 0 0; }}
            .content {{ background: #f9fafb; padding: 30px; border-radius: 0 0 10px 10px; }}
            .details {{ background: white; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #3b82f6; }}
            .detail-row {{ margin: 12px 0; }}
            .label {{ font-weight: bold; color: #6b7280; font-size: 12px; text-transform: uppercase; }}
            .value {{ color: #1f2937; font-size: 15px; }}
            .priority-badge {{ display: inline-block; padding: 8px 20px; border-radius: 20px; font-size: 14px; font-weight: bold; color: white; background: #ef4444; }}
            .text-box {{ background: #dbeafe; padding: 15px; border-radius: 8px; margin: 10px 0; }}
            h1 {{ margin: 0; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>💼 New Sponsorship Application</h1>
            </div>
            <div class="content">
                <div class="priority-badge">🔥 HIGH PRIORITY - NEW SPONSOR</div>
                
                <div class="details">
                    <div class="detail-row">
                        <div class="label">Application ID</div>
                        <div class="value">{application_id}</div>
                    </div>
                    <div class="detail-row">
                        <div class="label">Organization</div>
                        <div class="value" style="font-weight:bold;font-size:18px;">{organization_name}</div>
                    </div>
                    <div class="detail-row">
                        <div class="label">Industry</div>
                        <div class="value">{industry}</div>
                    </div>
                    <div class="detail-row">
                        <div class="label">Contact Person</div>
                        <div class="value">{contact_person}</div>
                    </div>
                    <div class="detail-row">
                        <div class="label">Email</div>
                        <div class="value"><a href="mailto:{email}">{email}</a></div>
                    </div>
                    <div class="detail-row">
                        <div class="label">Phone</div>
                        <div class="value">{phone_number}</div>
                    </div>
                    <div class="detail-row">
                        <div class="label">Interested Tiers</div>
                        <div class="value">{sponsorship_tiers}</div>
                    </div>
                    <div class="detail-row">
                        <div class="label">Booth Interest</div>
                        <div class="value">{booth_interest}</div>
                    </div>
                    <div class="detail-row">
                        <div class="label">Submitted</div>
                        <div class="value">{submission_date}</div>
                    </div>
                </div>
                
                <div class="text-box">
                    <div class="label">Sponsorship Goals</div>
                    <p>{sponsorship_goals}</p>
                </div>
                
                <div class="text-box">
                    <div class="label">How They Heard About AXI</div>
                    <p>{how_heard}</p>
                </div>
                
                <p style="text-align:center;margin-top:20px;color:#6b7280;font-size:12px;">
                    💡 Click Reply to respond directly to the applicant
                </p>
            </div>
        </div>
    </body>
    </html>
    """
    
    try:
        result = await graph_client.send_admin_notification(
            admin_emails=admin_emails,
            subject=f"[Sponsorship] 💰 New Application - {application_data['organization_name']}",
            template_html=email_template,
            template_vars={
                "application_id": application_data['application_id'],
                "organization_name": application_data['organization_name'],
                "industry": application_data['industry'],
                "contact_person": application_data['contact_person_name'],
                "email": application_data['email'],
                "phone_number": application_data['phone_number'],
                "sponsorship_tiers": tiers_html,
                "booth_interest": "Yes ✅" if application_data.get('booth_interest') else "No",
                "sponsorship_goals": application_data['sponsorship_goals'],
                "how_heard": application_data['how_heard_about_axi'],
                "submission_date": application_data['submitted_at'].strftime("%B %d, %Y at %I:%M %p")
            },
            reply_to_applicant=application_data['email']
        )
        print(f"✅ Admin notified about sponsorship application from {application_data['organization_name']}")
        return {"status": "sent", "type": "admin_sponsorship_notification"}
    except Exception as e:
        print(f"⚠️ Failed to send admin sponsorship notification: {e}")
        return {"status": "failed", "type": "admin_sponsorship_notification", "error": str(e)}


# ============================================================
# VOLUNTEER NOTIFICATIONS
# ============================================================

async def notify_volunteer_application_received(
    application_data: dict,
    graph_client: MicrosoftGraphClientPublic
) -> dict:
    """Send confirmation email for volunteer application."""
    
    email_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: linear-gradient(135deg, #10b981 0%, #059669 100%); color: white; padding: 30px; border-radius: 10px 10px 0 0; }}
            .content {{ background: #f9fafb; padding: 30px; border-radius: 0 0 10px 10px; }}
            .application-details {{ background: white; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #10b981; }}
            .detail-row {{ margin: 10px 0; }}
            .label {{ font-weight: bold; color: #6b7280; }}
            .value {{ color: #1f2937; }}
            .status-badge {{ display: inline-block; padding: 8px 20px; border-radius: 20px; font-size: 14px; font-weight: bold; color: white; background: #10b981; margin: 15px 0; }}
            .footer {{ text-align: center; margin-top: 20px; color: #6b7280; font-size: 12px; }}
            .cta-button {{ display: inline-block; padding: 12px 30px; background: #10b981; color: white; text-decoration: none; border-radius: 6px; font-weight: bold; margin-top: 20px; }}
            h1 {{ margin: 0; }}
            h3 {{ margin-top: 0; color: #059669; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🌟 Volunteer Application Received</h1>
            </div>
            <div class="content">
                <p>Hi <strong>{full_name}</strong>,</p>
                <p>Thank you for your interest in volunteering with Ideation Axis Group!</p>
                
                <div class="status-badge">APPLICATION UNDER REVIEW</div>
                
                <div class="application-details">
                    <h3>Your Volunteer Profile</h3>
                    <div class="detail-row">
                        <span class="label">Application ID:</span><br>
                        <span class="value">{application_id}</span>
                    </div>
                    <div class="detail-row">
                        <span class="label">Current Role:</span><br>
                        <span class="value">{current_role}</span>
                    </div>
                    <div class="detail-row">
                        <span class="label">Availability:</span><br>
                        <span class="value">📅 {availability}</span>
                    </div>
                    <div class="detail-row">
                        <span class="label">Submitted:</span><br>
                        <span class="value">{submission_date}</span>
                    </div>
                </div>
                
                <p><strong>Next Steps:</strong></p>
                <ul>
                    <li>Our volunteer coordinator will review your application within 3-5 business days</li>
                    <li>We'll contact you for a brief orientation call if your skills match our needs</li>
                    <li>You'll receive information about upcoming volunteer opportunities</li>
                </ul>
                
                <div style="text-align: center;">
                    <a href="https://ideationaxis.com/careers" class="cta-button">Learn More</a>
                </div>
                
                <div class="footer">
                    <p>We're excited about the possibility of working with you!</p>
                    <p>Best regards,<br>The Ideation Axis Group Volunteer Team</p>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    
    try:
        result = await graph_client.send_user_confirmation(
            to_email=application_data['email'],
            subject=f"Volunteer Application Received - {application_data['full_name']}",
            template_html=email_template,
            template_vars={
                "full_name": application_data['full_name'],
                "application_id": application_data['application_id'],
                "current_role": application_data['current_role'],
                "availability": application_data['availability'].replace('_', ' ').title(),
                "submission_date": application_data['submitted_at'].strftime("%B %d, %Y at %I:%M %p")
            },
            department="volunteer"
        )
        print(f"✅ Volunteer confirmation sent to {application_data['email']}")
        return {"status": "sent", "email": application_data['email'], "type": "volunteer_confirmation"}
    except Exception as e:
        print(f"⚠️ Failed to send volunteer confirmation: {e}")
        return {"status": "failed", "email": application_data['email'], "type": "volunteer_confirmation", "error": str(e)}


async def notify_admin_new_volunteer_application(
    application_data: dict,
    graph_client: MicrosoftGraphClientPublic,
    admin_emails: list = ADMIN_EMAILS
) -> dict:
    """Notify admin team about new volunteer application."""
    
    # Parse volunteer roles
    try:
        roles_list = json.loads(application_data['volunteer_roles'])
        roles_html = "".join([f'<span style="display:inline-block;padding:5px 12px;border-radius:15px;font-size:12px;font-weight:bold;color:white;background:#10b981;margin:3px;">{r}</span>' for r in roles_list])
    except:
        roles_html = '<span>Not specified</span>'
    
    # Parse skills
    skills = application_data.get('skills', '')
    if skills:
        skills_list = [s.strip() for s in skills.split(',')]
        skills_html = "".join([f'<span style="display:inline-block;padding:5px 12px;border-radius:15px;font-size:12px;font-weight:bold;color:#065f46;background:#d1fae5;margin:3px;">{s}</span>' for s in skills_list])
    else:
        skills_html = '<span>Not specified</span>'
    
    email_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: linear-gradient(135deg, #10b981 0%, #059669 100%); color: white; padding: 30px; border-radius: 10px 10px 0 0; }}
            .content {{ background: #f9fafb; padding: 30px; border-radius: 0 0 10px 10px; }}
            .details {{ background: white; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #10b981; }}
            .detail-row {{ margin: 12px 0; }}
            .label {{ font-weight: bold; color: #6b7280; font-size: 12px; text-transform: uppercase; }}
            .value {{ color: #1f2937; font-size: 15px; }}
            .priority-badge {{ display: inline-block; padding: 8px 20px; border-radius: 20px; font-size: 14px; font-weight: bold; color: white; background: #10b981; }}
            .text-box {{ background: #d1fae5; padding: 15px; border-radius: 8px; margin: 10px 0; }}
            h1 {{ margin: 0; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🌟 New Volunteer Application</h1>
            </div>
            <div class="content">
                <div class="priority-badge">NEW APPLICATION</div>
                
                <div class="details">
                    <div class="detail-row">
                        <div class="label">Application ID</div>
                        <div class="value">{application_id}</div>
                    </div>
                    <div class="detail-row">
                        <div class="label">Full Name</div>
                        <div class="value">{full_name}</div>
                    </div>
                    <div class="detail-row">
                        <div class="label">Email</div>
                        <div class="value"><a href="mailto:{email}">{email}</a></div>
                    </div>
                    <div class="detail-row">
                        <div class="label">Phone</div>
                        <div class="value">{phone_number}</div>
                    </div>
                    <div class="detail-row">
                        <div class="label">Current Role</div>
                        <div class="value">{current_role}</div>
                    </div>
                    <div class="detail-row">
                        <div class="label">Age Range</div>
                        <div class="value">{age_range}</div>
                    </div>
                    <div class="detail-row">
                        <div class="label">Preferred Roles</div>
                        <div class="value">{volunteer_roles}</div>
                    </div>
                    <div class="detail-row">
                        <div class="label">Skills</div>
                        <div class="value">{skills}</div>
                    </div>
                    <div class="detail-row">
                        <div class="label">Availability</div>
                        <div class="value">📅 {availability}</div>
                    </div>
                    <div class="detail-row">
                        <div class="label">Ambassador Interest</div>
                        <div class="value">{ambassador_interest}</div>
                    </div>
                    <div class="detail-row">
                        <div class="label">Submitted</div>
                        <div class="value">{submission_date}</div>
                    </div>
                </div>
                
                <div class="text-box">
                    <div class="label">Why They Want to Volunteer</div>
                    <p>{why_volunteer}</p>
                </div>
                
                <p style="text-align:center;margin-top:20px;color:#6b7280;font-size:12px;">
                    💡 Click Reply to respond directly to the applicant
                </p>
            </div>
        </div>
    </body>
    </html>
    """
    
    try:
        result = await graph_client.send_admin_notification(
            admin_emails=admin_emails,
            subject=f"[Volunteer] New Application - {application_data['full_name']}",
            template_html=email_template,
            template_vars={
                "application_id": application_data['application_id'],
                "full_name": application_data['full_name'],
                "email": application_data['email'],
                "phone_number": application_data['phone_number'],
                "current_role": application_data['current_role'],
                "age_range": application_data.get('age_range', 'Not specified').replace('_', ' ').title(),
                "volunteer_roles": roles_html,
                "skills": skills_html,
                "availability": application_data['availability'].replace('_', ' ').title(),
                "ambassador_interest": application_data.get('ambassador_interest') or 'Not specified',
                "why_volunteer": application_data['why_volunteer'],
                "submission_date": application_data['submitted_at'].strftime("%B %d, %Y at %I:%M %p")
            },
            reply_to_applicant=application_data['email']
        )
        print(f"✅ Admin notified about volunteer application from {application_data['full_name']}")
        return {"status": "sent", "type": "admin_volunteer_notification"}
    except Exception as e:
        print(f"⚠️ Failed to send admin volunteer notification: {e}")
        return {"status": "failed", "type": "admin_volunteer_notification", "error": str(e)}
    
    
async def notify_contact_message_received(
    message_data: dict,
    graph_client: MicrosoftGraphClientPublic
) -> dict:
    """Send confirmation email for contact form submission."""
    
    email_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: linear-gradient(135deg, #0A2463 0%, #1e40af 100%); color: white; padding: 30px; border-radius: 10px 10px 0 0; }}
            .content {{ background: #f9fafb; padding: 30px; border-radius: 0 0 10px 10px; }}
            .message-details {{ background: white; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #ffc007; }}
            .detail-row {{ margin: 10px 0; }}
            .label {{ font-weight: bold; color: #6b7280; }}
            .value {{ color: #1f2937; }}
            .status-badge {{ display: inline-block; padding: 8px 20px; border-radius: 20px; font-size: 14px; font-weight: bold; color: white; background: #10b981; margin: 15px 0; }}
            .footer {{ text-align: center; margin-top: 20px; color: #6b7280; font-size: 12px; }}
            .cta-button {{ display: inline-block; padding: 12px 30px; background: #ffc007; color: #0A2463; text-decoration: none; border-radius: 6px; font-weight: bold; margin-top: 20px; }}
            h1 {{ margin: 0; }}
            h3 {{ margin-top: 0; color: #0A2463; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>📬 Message Received</h1>
            </div>
            <div class="content">
                <p>Hi <strong>{full_name}</strong>,</p>
                <p>Thank you for reaching out to Ideation Axis Group! We've received your message and will get back to you as soon as possible.</p>
                
                <div class="status-badge">MESSAGE RECEIVED</div>
                
                <div class="message-details">
                    <h3>Your Message Summary</h3>
                    
                    <div class="detail-row">
                        <span class="label">Reference ID:</span><br>
                        <span class="value">{message_id}</span>
                    </div>
                    
                    <div class="detail-row">
                        <span class="label">Subject:</span><br>
                        <span class="value">{subject}</span>
                    </div>
                    
                    <div class="detail-row">
                        <span class="label">Submitted:</span><br>
                        <span class="value">{submission_date}</span>
                    </div>
                </div>
                
                <p><strong>What happens next?</strong></p>
                <ul>
                    <li>Our team typically responds within 1-2 business days</li>
                    <li>We'll reply to your email at {email}</li>
                    <li>For urgent matters, you can reach us on our social media channels</li>
                </ul>
                
                <div style="text-align: center;">
                    <a href="https://ideationaxis.com" class="cta-button">Visit Our Website</a>
                </div>
                
                <div class="footer">
                    <p>Thank you for getting in touch with us!</p>
                    <p>Best regards,<br>The Ideation Axis Group Team</p>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    
    try:
        result = await graph_client.send_user_confirmation(
            to_email=message_data['email'],
            subject=f"We've received your message - {message_data['subject']}",
            template_html=email_template,
            template_vars={
                "full_name": message_data['full_name'],
                "message_id": message_data['message_id'],
                "subject": message_data['subject'],
                "submission_date": message_data['submitted_at'].strftime("%B %d, %Y at %I:%M %p"),
                "email": message_data['email']
            },
            department="general"
        )
        print(f"✅ Contact message confirmation sent to {message_data['email']}")
        return {"status": "sent", "email": message_data['email'], "type": "contact_confirmation"}
    except Exception as e:
        print(f"⚠️ Failed to send contact confirmation: {e}")
        return {"status": "failed", "email": message_data['email'], "type": "contact_confirmation", "error": str(e)}


async def notify_admin_new_contact_message(
    message_data: dict,
    graph_client: MicrosoftGraphClientPublic,
    admin_emails: list = None
) -> dict:
    """Notify admin team about new contact form submission."""
    
    from app.constants.constants import ADMIN_EMAILS
    if admin_emails is None:
        admin_emails = ADMIN_EMAILS
    
    email_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: linear-gradient(135deg, #0A2463 0%, #1e40af 100%); color: white; padding: 30px; border-radius: 10px 10px 0 0; }}
            .content {{ background: #f9fafb; padding: 30px; border-radius: 0 0 10px 10px; }}
            .details {{ background: white; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #ffc007; }}
            .detail-row {{ margin: 12px 0; }}
            .label {{ font-weight: bold; color: #6b7280; font-size: 12px; text-transform: uppercase; }}
            .value {{ color: #1f2937; font-size: 15px; }}
            .priority-badge {{ display: inline-block; padding: 8px 20px; border-radius: 20px; font-size: 14px; font-weight: bold; color: white; background: #f59e0b; }}
            .text-box {{ background: #fef3c7; padding: 15px; border-radius: 8px; margin: 10px 0; }}
            h1 {{ margin: 0; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>📩 New Contact Form Submission</h1>
            </div>
            <div class="content">
                <div class="priority-badge">REQUIRES RESPONSE</div>
                
                <div class="details">
                    <div class="detail-row">
                        <div class="label">Reference ID</div>
                        <div class="value">{message_id}</div>
                    </div>
                    <div class="detail-row">
                        <div class="label">Name</div>
                        <div class="value">{full_name}</div>
                    </div>
                    <div class="detail-row">
                        <div class="label">Email</div>
                        <div class="value"><a href="mailto:{email}">{email}</a></div>
                    </div>
                    <div class="detail-row">
                        <div class="label">Phone</div>
                        <div class="value">{phone_number}</div>
                    </div>
                    <div class="detail-row">
                        <div class="label">Subject</div>
                        <div class="value">{subject}</div>
                    </div>
                    <div class="detail-row">
                        <div class="label">Submitted</div>
                        <div class="value">{submission_date}</div>
                    </div>
                </div>
                
                <div class="text-box">
                    <div class="label">Message</div>
                    <p>{message}</p>
                </div>
                
                <p style="text-align:center;margin-top:20px;color:#6b7280;font-size:12px;">
                    💡 Click Reply to respond directly to the sender
                </p>
            </div>
        </div>
    </body>
    </html>
    """
    
    try:
        result = await graph_client.send_admin_notification(
            admin_emails=admin_emails,
            subject=f"[Contact Form] {message_data['subject']} - {message_data['full_name']}",
            template_html=email_template,
            template_vars={
                "message_id": message_data['message_id'],
                "full_name": message_data['full_name'],
                "email": message_data['email'],
                "phone_number": message_data.get('phone_number') or 'Not provided',
                "subject": message_data['subject'],
                "message": message_data['message'],
                "submission_date": message_data['submitted_at'].strftime("%B %d, %Y at %I:%M %p")
            },
            reply_to_applicant=message_data['email']
        )
        print(f"✅ Admin notified about contact message from {message_data['full_name']}")
        return {"status": "sent", "type": "admin_contact_notification"}
    except Exception as e:
        print(f"⚠️ Failed to send admin contact notification: {e}")
        return {"status": "failed", "type": "admin_contact_notification", "error": str(e)}
    
async def notify_job_waitlist_confirmation(
    waitlist_data: dict,
    graph_client: MicrosoftGraphClientPublic
) -> dict:
    """Send confirmation email for job waitlist registration."""
    
    email_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: linear-gradient(135deg, #0A2463 0%, #1e40af 100%); color: white; padding: 30px; border-radius: 10px 10px 0 0; }}
            .content {{ background: #f9fafb; padding: 30px; border-radius: 0 0 10px 10px; }}
            .waitlist-details {{ background: white; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #ffc007; }}
            .detail-row {{ margin: 10px 0; }}
            .label {{ font-weight: bold; color: #6b7280; }}
            .value {{ color: #1f2937; }}
            .status-badge {{ display: inline-block; padding: 8px 20px; border-radius: 20px; font-size: 14px; font-weight: bold; color: white; background: #10b981; margin: 15px 0; }}
            .footer {{ text-align: center; margin-top: 20px; color: #6b7280; font-size: 12px; }}
            .cta-button {{ display: inline-block; padding: 12px 30px; background: #ffc007; color: #0A2463; text-decoration: none; border-radius: 6px; font-weight: bold; margin-top: 20px; }}
            h1 {{ margin: 0; }}
            h3 {{ margin-top: 0; color: #0A2463; }}
            .clock-emoji {{ font-size: 48px; text-align: center; margin: 20px 0; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>⏰ You're on the Waitlist!</h1>
            </div>
            <div class="content">
                <p>Hi <strong>{full_name}</strong>,</p>
                <p>Thank you for joining our job opportunities waitlist at Ideation Axis Group!</p>
                
                <div class="clock-emoji">🕐</div>
                
                <div class="status-badge">WAITLIST CONFIRMED</div>
                
                <div class="waitlist-details">
                    <h3>Your Waitlist Information</h3>
                    
                    <div class="detail-row">
                        <span class="label">Waitlist ID:</span><br>
                        <span class="value">{waitlist_id}</span>
                    </div>
                    
                    <div class="detail-row">
                        <span class="label">Preferred Role:</span><br>
                        <span class="value">{preferred_role}</span>
                    </div>
                    
                    <div class="detail-row">
                        <span class="label">Registered:</span><br>
                        <span class="value">{submission_date}</span>
                    </div>
                </div>
                
                <p><strong>What happens next?</strong></p>
                <ul>
                    <li>You'll be among the first to know when roles matching your interests open up</li>
                    <li>We'll send you notifications at {email}</li>
                    <li>Keep an eye on your inbox for new opportunities</li>
                    <li>Make sure to check your spam folder occasionally</li>
                </ul>
                
                <p><strong>Why join Ideation Axis Group?</strong></p>
                <ul>
                    <li>⚡ Ownership from day one</li>
                    <li>🏢 Build real companies</li>
                    <li>🎯 Results over credentials</li>
                </ul>
                
                <div style="text-align: center;">
                    <a href="https://ideationaxis.com/careers" class="cta-button">Explore Our Story</a>
                </div>
                
                <div class="footer">
                    <p>We're excited about the possibility of working with you!</p>
                    <p>Best regards,<br>The Ideation Axis Group Careers Team</p>
                    <p style="margin-top: 20px; font-size: 11px;">
                        Don't want to receive these updates? <a href="mailto:hello@ideationaxis.com?subject=Unsubscribe%20from%20Job%20Waitlist">Unsubscribe</a>
                    </p>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    
    try:
        result = await graph_client.send_user_confirmation(
            to_email=waitlist_data['email'],
            subject=f"You're on the Waitlist - {waitlist_data['preferred_role']}",
            template_html=email_template,
            template_vars={
                "full_name": waitlist_data['full_name'],
                "waitlist_id": waitlist_data['waitlist_id'],
                "preferred_role": waitlist_data['preferred_role'],
                "submission_date": waitlist_data['submitted_at'].strftime("%B %d, %Y at %I:%M %p"),
                "email": waitlist_data['email']
            },
            department="general"
        )
        print(f"✅ Job waitlist confirmation sent to {waitlist_data['email']}")
        return {"status": "sent", "email": waitlist_data['email'], "type": "waitlist_confirmation"}
    except Exception as e:
        print(f"⚠️ Failed to send waitlist confirmation: {e}")
        return {"status": "failed", "email": waitlist_data['email'], "type": "waitlist_confirmation", "error": str(e)}


async def notify_admin_new_waitlist_signup(
    waitlist_data: dict,
    graph_client: MicrosoftGraphClientPublic,
    admin_emails: list = None
) -> dict:
    """Notify admin team about new job waitlist signup."""
    
    from app.constants.constants import ADMIN_EMAILS
    if admin_emails is None:
        admin_emails = ADMIN_EMAILS
    
    email_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: linear-gradient(135deg, #0A2463 0%, #1e40af 100%); color: white; padding: 30px; border-radius: 10px 10px 0 0; }}
            .content {{ background: #f9fafb; padding: 30px; border-radius: 0 0 10px 10px; }}
            .details {{ background: white; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #ffc007; }}
            .detail-row {{ margin: 12px 0; }}
            .label {{ font-weight: bold; color: #6b7280; font-size: 12px; text-transform: uppercase; }}
            .value {{ color: #1f2937; font-size: 15px; }}
            .priority-badge {{ display: inline-block; padding: 8px 20px; border-radius: 20px; font-size: 14px; font-weight: bold; color: white; background: #10b981; }}
            h1 {{ margin: 0; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>👤 New Job Waitlist Signup</h1>
            </div>
            <div class="content">
                <div class="priority-badge">NEW CANDIDATE</div>
                
                <div class="details">
                    <div class="detail-row">
                        <div class="label">Waitlist ID</div>
                        <div class="value">{waitlist_id}</div>
                    </div>
                    <div class="detail-row">
                        <div class="label">Full Name</div>
                        <div class="value">{full_name}</div>
                    </div>
                    <div class="detail-row">
                        <div class="label">Email</div>
                        <div class="value"><a href="mailto:{email}">{email}</a></div>
                    </div>
                    <div class="detail-row">
                        <div class="label">Phone</div>
                        <div class="value">{phone_number}</div>
                    </div>
                    <div class="detail-row">
                        <div class="label">LinkedIn</div>
                        <div class="value">{linkedin_url}</div>
                    </div>
                    <div class="detail-row">
                        <div class="label">Preferred Role</div>
                        <div class="value" style="font-weight:bold;color:#0A2463;">{preferred_role}</div>
                    </div>
                    <div class="detail-row">
                        <div class="label">Registered</div>
                        <div class="value">{submission_date}</div>
                    </div>
                </div>
                
                <p style="text-align:center;margin-top:20px;color:#6b7280;font-size:12px;">
                    💡 When a matching role opens, notify this candidate from the admin panel
                </p>
            </div>
        </div>
    </body>
    </html>
    """
    
    try:
        result = await graph_client.send_admin_notification(
            admin_emails=admin_emails,
            subject=f"[Job Waitlist] {waitlist_data['preferred_role']} - {waitlist_data['full_name']}",
            template_html=email_template,
            template_vars={
                "waitlist_id": waitlist_data['waitlist_id'],
                "full_name": waitlist_data['full_name'],
                "email": waitlist_data['email'],
                "phone_number": waitlist_data['phone_number'],
                "linkedin_url": waitlist_data.get('linkedin_url') or 'Not provided',
                "preferred_role": waitlist_data['preferred_role'],
                "submission_date": waitlist_data['submitted_at'].strftime("%B %d, %Y at %I:%M %p")
            },
            reply_to_applicant=waitlist_data['email']
        )
        print(f"✅ Admin notified about waitlist signup from {waitlist_data['full_name']}")
        return {"status": "sent", "type": "admin_waitlist_notification"}
    except Exception as e:
        print(f"⚠️ Failed to send admin waitlist notification: {e}")
        return {"status": "failed", "type": "admin_waitlist_notification", "error": str(e)}
    
async def notify_ticket_purchase_confirmation(
    ticket_data: dict,
    graph_client: MicrosoftGraphClientPublic
) -> dict:
    """
    Send ticket purchase confirmation email with PDF attachment.
    
    Args:
        ticket_data: Dictionary containing:
            - tickets: List of ticket objects
            - event: Event object
            - payment_reference: str
            - attendee_email: str
            - attendee_name: str
    """
    
    email_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: linear-gradient(135deg, #0A2463 0%, #1e40af 100%); color: white; padding: 30px; border-radius: 10px 10px 0 0; text-align: center; }}
            .content {{ background: #f9fafb; padding: 30px; border-radius: 0 0 10px 10px; }}
            .ticket-card {{ background: white; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #ffc007; }}
            .detail-row {{ margin: 12px 0; padding: 8px 0; border-bottom: 1px solid #f3f4f6; }}
            .label {{ font-weight: bold; color: #6b7280; font-size: 12px; text-transform: uppercase; }}
            .value {{ color: #1f2937; font-size: 15px; margin-top: 4px; }}
            .status-badge {{ display: inline-block; padding: 10px 24px; border-radius: 20px; font-size: 14px; font-weight: bold; color: white; background: #10b981; margin: 15px 0; }}
            .ticket-number {{ font-family: 'Courier New', monospace; font-size: 18px; font-weight: bold; color: #0A2463; background: #fef3c7; padding: 8px 16px; border-radius: 6px; display: inline-block; }}
            .footer {{ text-align: center; margin-top: 30px; color: #6b7280; font-size: 12px; padding-top: 20px; border-top: 1px solid #e5e7eb; }}
            .important-box {{ background: #fef3c7; border-left: 4px solid #ffc007; padding: 15px; border-radius: 6px; margin: 20px 0; }}
            h1 {{ margin: 0; font-size: 28px; }}
            h3 {{ margin-top: 0; color: #0A2463; }}
            .emoji {{ font-size: 48px; margin: 10px 0; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div class="emoji">🎉</div>
                <h1>Ticket Purchase Confirmed!</h1>
            </div>
            <div class="content">
                <p>Hi <strong>{attendee_name}</strong>,</p>
                <p>Great news! Your ticket purchase has been confirmed. Get ready for an amazing experience!</p>
                
                <div style="text-align: center;">
                    <div class="status-badge">✓ PAYMENT CONFIRMED</div>
                </div>
                
                <div class="ticket-card">
                    <h3>📅 Event Details</h3>
                    <div class="detail-row">
                        <div class="label">Event</div>
                        <div class="value">{event_name}</div>
                    </div>
                    <div class="detail-row">
                        <div class="label">Date & Time</div>
                        <div class="value">{event_date} at {event_time}</div>
                    </div>
                    <div class="detail-row">
                        <div class="label">Venue</div>
                        <div class="value">{venue_name}<br><span style="font-size: 13px; color: #6b7280;">{venue_address}</span></div>
                    </div>
                </div>
                
                <div class="ticket-card">
                    <h3>🎫 Your Ticket(s)</h3>
                    {ticket_list}
                </div>
                
                <div class="important-box">
                    <strong>📎 Your ticket(s) are attached to this email as a PDF.</strong>
                    <p style="margin: 8px 0 0 0; font-size: 14px;">You can also access your tickets anytime by visiting our website and entering your email.</p>
                </div>
                
                <div class="ticket-card">
                    <h3>ℹ️ Important Information</h3>
                    <ul style="margin: 10px 0; padding-left: 20px;">
                        <li>Please bring your ticket (digital or printed) to the event</li>
                        <li>The QR code on your ticket will be scanned at the entrance</li>
                        <li>Doors open 30 minutes before the event starts</li>
                        <li>For any questions, reply to this email or contact: events@ideationaxis.com</li>
                    </ul>
                </div>
                
                <div style="text-align: center; margin: 30px 0;">
                    <p style="font-size: 16px; color: #0A2463; font-weight: bold;">We can't wait to see you there! 🎉</p>
                </div>
                
                <div class="footer">
                    <p><strong>Payment Reference:</strong> {payment_reference}</p>
                    <p>Thank you for choosing Ideation Axis Group events!</p>
                    <p style="margin-top: 20px;">
                        <strong>Ideation Axis Group</strong><br>
                        Building Africa's Future Through Innovation<br>
                        <a href="https://ideationaxis.com">ideationaxis.com</a>
                    </p>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    
    # Generate ticket list HTML
    ticket_list_html = ""
    for i, ticket in enumerate(ticket_data['tickets'], 1):
        ticket_list_html += f"""
        <div class="detail-row">
            <div class="label">Ticket #{i} - {ticket['ticket_type']}</div>
            <div class="value">
                <span class="ticket-number">{ticket['ticket_number']}</span>
            </div>
        </div>
        """
    
    # Generate PDF attachments for each ticket
    attachments = []
    for ticket in ticket_data['tickets']:
        pdf_bytes = await generate_ticket_pdf({
            'ticket_number': ticket['ticket_number'],
            'event_name': ticket_data['event']['title'],
            'event_date': ticket_data['event']['event_date'].strftime("%B %d, %Y"),
            'event_time': ticket_data['event']['event_time'],
            'venue_name': ticket_data['event']['venue_name'],
            'venue_address': ticket_data['event']['venue_address'],
            'attendee_name': ticket['attendee_name'],
            'attendee_email': ticket['attendee_email'],
            'ticket_type': ticket['ticket_type'],
            'qr_code': ticket['qr_code'],
            'price_paid': float(ticket['price_paid'])
        })
        
        # Convert PDF to base64 for email attachment
        pdf_base64 = base64.b64encode(pdf_bytes).decode()
        
        attachments.append({
            "@odata.type": "#microsoft.graph.fileAttachment",
            "name": f"ticket_{ticket['ticket_number']}.pdf",
            "contentType": "application/pdf",
            "contentBytes": pdf_base64
        })
    
    try:
        result = await graph_client.send_email(
            to_emails=[ticket_data['attendee_email']],
            subject=f"Your Tickets for {ticket_data['event']['title']} 🎉",
            body_html=email_template.format(
                attendee_name=ticket_data['attendee_name'],
                event_name=ticket_data['event']['title'],
                event_date=ticket_data['event']['event_date'].strftime("%B %d, %Y"),
                event_time=ticket_data['event']['event_time'],
                venue_name=ticket_data['event']['venue_name'],
                venue_address=ticket_data['event']['venue_address'],
                ticket_list=ticket_list_html,
                payment_reference=ticket_data['payment_reference']
            ),
            department="events",
            attachments=attachments
        )
        
        print(f"✅ Ticket confirmation email sent to {ticket_data['attendee_email']} with {len(attachments)} PDF(s)")
        return {"status": "sent", "email": ticket_data['attendee_email'], "type": "ticket_confirmation", "attachments": len(attachments)}
    
    except Exception as e:
        print(f"⚠️ Failed to send ticket confirmation email: {e}")
        return {"status": "failed", "email": ticket_data['attendee_email'], "type": "ticket_confirmation", "error": str(e)}
    
async def notify_admin_new_ticket_purchase(
    ticket_data: dict,
    graph_client: MicrosoftGraphClientPublic,
    admin_emails: list = ADMIN_EMAILS
) -> dict:
    """
    Notify admin team about new ticket purchase.
    
    Args:
        ticket_data: Dictionary containing:
            - tickets: List of ticket objects
            - event: Event object
            - payment_reference: str
            - attendee_email: str
            - attendee_name: str
            - payment_amount: float
            - payment_date: datetime
    """
    
    # Build ticket list HTML
    ticket_list_html = ""
    for i, ticket in enumerate(ticket_data['tickets'], 1):
        ticket_list_html += f"""
        <div class="detail-row">
            <div class="label">Ticket #{i}</div>
            <div class="value">
                <strong>{ticket['ticket_type']}</strong><br>
                <span class="ticket-number">{ticket['ticket_number']}</span><br>
                <span style="font-size: 13px; color: #6b7280;">
                    {ticket['attendee_name']} • {ticket['attendee_email']}
                </span><br>
                <span style="font-size: 14px; color: #059669; font-weight: bold;">
                    GH₵ {float(ticket['price_paid']):.2f}
                </span>
            </div>
        </div>
        """
    
    # Calculate total amount
    total_amount = sum(float(ticket['price_paid']) for ticket in ticket_data['tickets'])
    ticket_count = len(ticket_data['tickets'])
    
    email_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 700px; margin: 0 auto; padding: 20px; }}
            .header {{ 
                background: linear-gradient(135deg, #0A2463 0%, #1449c9 100%); 
                color: white; 
                padding: 30px; 
                border-radius: 10px 10px 0 0; 
            }}
            .content {{ background: #f9fafb; padding: 30px; border-radius: 0 0 10px 10px; }}
            .details {{ 
                background: white; 
                padding: 20px; 
                border-radius: 8px; 
                margin: 20px 0; 
                border-left: 5px solid #10b981; 
            }}
            .detail-row {{ 
                margin: 12px 0; 
                padding: 10px 0; 
                border-bottom: 1px solid #f3f4f6; 
            }}
            .detail-row:last-child {{ border-bottom: none; }}
            .label {{ 
                font-weight: bold; 
                color: #6b7280; 
                font-size: 11px; 
                text-transform: uppercase; 
                letter-spacing: 0.5px;
            }}
            .value {{ color: #1f2937; font-size: 15px; margin-top: 4px; }}
            .priority-badge {{ 
                display: inline-block; 
                padding: 10px 24px; 
                border-radius: 20px; 
                font-size: 14px; 
                font-weight: bold; 
                color: white; 
                background: #10b981; 
            }}
            .ticket-number {{ 
                font-family: 'Courier New', monospace; 
                font-size: 14px; 
                font-weight: bold; 
                color: #0A2463; 
                background: #dbeafe; 
                padding: 4px 10px; 
                border-radius: 4px; 
                display: inline-block;
            }}
            .total-box {{
                background: linear-gradient(135deg, #10b981 0%, #059669 100%);
                color: white;
                padding: 20px;
                border-radius: 8px;
                margin: 20px 0;
                text-align: center;
            }}
            .total-amount {{
                font-size: 32px;
                font-weight: bold;
                margin: 10px 0;
            }}
            .stats-grid {{
                display: grid;
                grid-template-columns: repeat(2, 1fr);
                gap: 15px;
                margin: 20px 0;
            }}
            .stat-card {{
                background: white;
                padding: 15px;
                border-radius: 8px;
                text-align: center;
                border: 2px solid #e5e7eb;
            }}
            .stat-number {{
                font-size: 24px;
                font-weight: bold;
                color: #0A2463;
            }}
            .stat-label {{
                font-size: 12px;
                color: #6b7280;
                text-transform: uppercase;
                margin-top: 5px;
            }}
            h1 {{ margin: 0; font-size: 28px; }}
            h3 {{ color: #0A2463; margin-top: 0; }}
            .emoji {{ font-size: 48px; text-align: center; margin: 10px 0; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🎉 New Ticket Purchase!</h1>
                <p style="margin: 10px 0 0 0; opacity: 0.9;">A new ticket order has been completed</p>
            </div>
            
            <div class="content">
                <div style="text-align: center; margin-bottom: 20px;">
                    <div class="priority-badge">✓ PAYMENT CONFIRMED</div>
                </div>
                
                <div class="total-box">
                    <div style="font-size: 16px; opacity: 0.9;">Total Payment Received</div>
                    <div class="total-amount">GH₵ {total_amount:.2f}</div>
                    <div style="font-size: 14px; opacity: 0.9;">{ticket_count} ticket(s) purchased</div>
                </div>
                
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-number">{ticket_count}</div>
                        <div class="stat-label">Tickets Sold</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">GH₵ {total_amount:.2f}</div>
                        <div class="stat-label">Revenue</div>
                    </div>
                </div>
                
                <div class="details">
                    <h3>📅 Event Information</h3>
                    
                    <div class="detail-row">
                        <div class="label">Event Name</div>
                        <div class="value" style="font-size: 18px; font-weight: bold; color: #0A2463;">
                            {event_name}
                        </div>
                    </div>
                    
                    <div class="detail-row">
                        <div class="label">Event Date & Time</div>
                        <div class="value">{event_date} at {event_time}</div>
                    </div>
                    
                    <div class="detail-row">
                        <div class="label">Venue</div>
                        <div class="value">
                            {venue_name}<br>
                            <span style="font-size: 13px; color: #6b7280;">{venue_address}</span>
                        </div>
                    </div>
                </div>
                
                <div class="details">
                    <h3>👤 Customer Information</h3>
                    
                    <div class="detail-row">
                        <div class="label">Name</div>
                        <div class="value">{attendee_name}</div>
                    </div>
                    
                    <div class="detail-row">
                        <div class="label">Email</div>
                        <div class="value">
                            <a href="mailto:{attendee_email}" style="color: #1449c9; text-decoration: none;">
                                {attendee_email}
                            </a>
                        </div>
                    </div>
                    
                    <div class="detail-row">
                        <div class="label">Payment Reference</div>
                        <div class="value" style="font-family: 'Courier New', monospace; font-size: 13px; color: #6b7280;">
                            {payment_reference}
                        </div>
                    </div>
                    
                    <div class="detail-row">
                        <div class="label">Payment Date</div>
                        <div class="value">{payment_date}</div>
                    </div>
                </div>
                
                <div class="details">
                    <h3>🎫 Ticket Details</h3>
                    {ticket_list}
                </div>
                
                <div style="background: #dbeafe; padding: 18px; border-radius: 8px; margin: 20px 0; text-align: center;">
                    <p style="margin: 0; color: #1e40af; font-size: 14px;">
                        ✅ <strong>Tickets have been confirmed and emailed to the customer</strong>
                    </p>
                </div>
                
                <div style="text-align: center; margin-top: 25px; padding-top: 20px; border-top: 1px solid #e5e7eb;">
                    <p style="color: #6b7280; font-size: 12px; margin: 0;">
                        <strong>Ideation Axis Group</strong> • Event Management System<br>
                        This is an automated notification for ticket sales
                    </p>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    
    try:
        result = await graph_client.send_admin_notification(
            admin_emails=admin_emails,
            subject=f"💰 New Ticket Sale - {ticket_data['event']['title']} - GH₵ {total_amount:.2f}",
            template_html=email_template,
            template_vars={
                "event_name": ticket_data['event']['title'],
                "event_date": ticket_data['event']['event_date'].strftime("%B %d, %Y"),
                "event_time": ticket_data['event']['event_time'],
                "venue_name": ticket_data['event']['venue_name'],
                "venue_address": ticket_data['event']['venue_address'],
                "attendee_name": ticket_data['attendee_name'],
                "attendee_email": ticket_data['attendee_email'],
                "payment_reference": ticket_data['payment_reference'],
                "payment_date": ticket_data.get('payment_date', datetime.utcnow()).strftime("%B %d, %Y at %I:%M %p"),
                "ticket_list": ticket_list_html,
                "total_amount": total_amount,
                "ticket_count": ticket_count
            },
            reply_to_applicant=ticket_data['attendee_email']
        )
        
        print(f"✅ Admin notified about ticket purchase for {ticket_data['event']['title']}")
        return {
            "status": "sent", 
            "type": "admin_ticket_purchase_notification",
            "recipients": len(admin_emails)
        }
    
    except Exception as e:
        print(f"⚠️ Failed to send admin ticket purchase notification: {e}")
        return {
            "status": "failed", 
            "type": "admin_ticket_purchase_notification", 
            "error": str(e)
        }
    
async def notify_becoming_first_registration_confirmation(
    registration_data: dict,
    graph_client: MicrosoftGraphClientPublic
) -> dict:
    """Send confirmation email for Becoming The First event registration."""
    
    email_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: linear-gradient(135deg, #0a2463 0%, #1449c9 100%); color: white; padding: 30px; border-radius: 10px 10px 0 0; text-align: center; }}
            .content {{ background: #f9fafb; padding: 30px; border-radius: 0 0 10px 10px; }}
            .event-details {{ background: white; padding: 25px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #FFC007; }}
            .detail-row {{ margin: 15px 0; display: flex; align-items: start; }}
            .icon {{ font-size: 24px; margin-right: 12px; min-width: 30px; }}
            .detail-content {{ flex: 1; }}
            .label {{ font-weight: bold; color: #6b7280; font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px; }}
            .value {{ color: #1f2937; font-size: 16px; margin-top: 4px; }}
            .status-badge {{ display: inline-block; padding: 12px 30px; border-radius: 25px; font-size: 14px; font-weight: bold; color: white; background: #10b981; margin: 20px 0; }}
            .meeting-link-box {{ background: linear-gradient(135deg, #FFC007 0%, #f59e0b 100%); padding: 25px; border-radius: 12px; margin: 25px 0; text-align: center; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
            .meeting-link-button {{ display: inline-block; padding: 15px 40px; background: #0a2463; color: white; text-decoration: none; border-radius: 8px; font-weight: bold; font-size: 16px; margin-top: 10px; transition: transform 0.2s; }}
            .meeting-link-button:hover {{ transform: translateY(-2px); }}
            .speaker-card {{ background: linear-gradient(135deg, #f3f4f6 0%, #e5e7eb 100%); padding: 20px; border-radius: 10px; margin: 20px 0; text-align: center; }}
            .speaker-name {{ font-size: 20px; font-weight: bold; color: #0a2463; margin: 10px 0; }}
            .speaker-title {{ color: #6b7280; font-size: 14px; font-style: italic; }}
            .footer {{ text-align: center; margin-top: 30px; color: #6b7280; font-size: 12px; padding-top: 20px; border-top: 1px solid #e5e7eb; }}
            .important-note {{ background: #fef3c7; border-left: 4px solid #FFC007; padding: 15px; border-radius: 6px; margin: 20px 0; }}
            h1 {{ margin: 0; font-size: 32px; }}
            h3 {{ margin-top: 0; color: #0a2463; font-size: 22px; }}
            .emoji {{ font-size: 48px; margin: 10px 0; }}
            ul {{ margin: 10px 0; padding-left: 20px; }}
            li {{ margin: 8px 0; color: #4b5563; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div class="emoji">✨</div>
                <h1>You're Registered!</h1>
                <p style="margin: 10px 0 0 0; font-size: 18px; opacity: 0.95;">Becoming The First: From Nothing to New Beginnings</p>
            </div>
            <div class="content">
                <p>Hi <strong>{full_name}</strong>,</p>
                <p>Thank you for registering for <strong>Becoming The First</strong>! We're thrilled to have you join us for this transformative leadership conversation.</p>
                
                <div style="text-align: center;">
                    <div class="status-badge">✓ REGISTRATION CONFIRMED</div>
                </div>
                
                <div class="event-details">
                    <h3>📅 Event Details</h3>
                    
                    <div class="detail-row">
                        <div class="icon">📆</div>
                        <div class="detail-content">
                            <div class="label">Date</div>
                            <div class="value">{event_date}</div>
                        </div>
                    </div>
                    
                    <div class="detail-row">
                        <div class="icon">🕐</div>
                        <div class="detail-content">
                            <div class="label">Time</div>
                            <div class="value">{event_time}</div>
                        </div>
                    </div>
                    
                    <div class="detail-row">
                        <div class="icon">🌐</div>
                        <div class="detail-content">
                            <div class="label">Location</div>
                            <div class="value">{event_location}</div>
                        </div>
                    </div>
                    
                    <div class="detail-row">
                        <div class="icon">🎫</div>
                        <div class="detail-content">
                            <div class="label">Registration ID</div>
                            <div class="value" style="font-family: 'Courier New', monospace; font-size: 14px; color: #6b7280;">{registration_id}</div>
                        </div>
                    </div>
                </div>
                
                <div class="meeting-link-box">
                    <div style="color: #0a2463; font-size: 20px; font-weight: bold; margin-bottom: 10px;">
                        🎥 Join the Conversation
                    </div>
                    <p style="color: #1f2937; margin: 10px 0; font-size: 14px;">
                        Click the button below to join us on Google Meet
                    </p>
                    <a href="{meeting_link}" class="meeting-link-button">
                        JOIN GOOGLE MEET
                    </a>
                    <p style="color: #6b7280; margin-top: 15px; font-size: 12px;">
                        Meeting Link: <a href="{meeting_link}" style="color: #0a2463;">{meeting_link}</a>
                    </p>
                </div>
                
                <div class="speaker-card">
                    <div class="emoji" style="font-size: 36px;">🎤</div>
                    <div class="speaker-name">Philip Appiah Gyimah</div>
                    <div class="speaker-title">CEO & Founder, Ideation Axis Group</div>
                    <p style="margin-top: 15px; color: #4b5563; font-size: 14px;">
                        An extraordinary journey of faith, resilience, and impact
                    </p>
                </div>
                
                <div class="important-note">
                    <strong>📌 Important Reminders:</strong>
                    <ul style="margin-top: 10px;">
                        <li>Save the meeting link above or add the event to your calendar</li>
                        <li>Join a few minutes early to test your audio and video</li>
                        <li>Come prepared with questions for Philip!</li>
                        <li>This is a FREE event - no payment required</li>
                    </ul>
                </div>
                
                <div class="event-details">
                    <h3>💡 What to Expect</h3>
                    <p style="color: #4b5563;">During this transformative conversation, you'll discover:</p>
                    <ul>
                        <li><strong>Faith & Resilience:</strong> How to overcome obstacles and stay committed to your vision</li>
                        <li><strong>From Nothing to New Beginnings:</strong> Building something meaningful without capital</li>
                        <li><strong>Leadership Lessons:</strong> Practical insights from Philip's entrepreneurial journey</li>
                        <li><strong>Q&A Session:</strong> Get your questions answered directly</li>
                    </ul>
                </div>
                
                <div style="text-align: center; margin: 30px 0;">
                    <p style="font-size: 18px; color: #0a2463; font-weight: bold;">
                        We can't wait to see you there! 🎉
                    </p>
                    <p style="color: #6b7280; font-size: 14px; margin-top: 10px;">
                        Have questions? Reply to this email or contact us at events@ideationaxis.com
                    </p>
                </div>
                
                <div class="footer">
                    <p><strong>Ideation Axis Group LTD.</strong><br>
                    Africa's Startup Engine<br>
                    <a href="https://ideationaxis.com" style="color: #0a2463;">ideationaxis.com</a></p>
                    <p style="margin-top: 15px; font-size: 11px;">
                        Follow us: <a href="#" style="color: #0a2463;">@IdeationAxisGroup</a>
                    </p>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    
    try:
        result = await graph_client.send_user_confirmation(
            to_email=registration_data['email'],
            subject=f"You're Registered! Becoming The First - Dec 10th, 7PM GMT 🎉",
            template_html=email_template,
            template_vars={
                "full_name": registration_data['full_name'],
                "registration_id": registration_data['registration_id'],
                "event_date": registration_data['event_date'],
                "event_time": registration_data['event_time'],
                "event_location": registration_data['event_location'],
                "meeting_link": registration_data['meeting_link'],
                "submission_date": registration_data['submitted_at'].strftime("%B %d, %Y at %I:%M %p")
            },
            department="events"
        )
        print(f"✅ Becoming The First registration confirmation sent to {registration_data['email']}")
        return {"status": "sent", "email": registration_data['email'], "type": "becoming_first_confirmation"}
    except Exception as e:
        print(f"⚠️ Failed to send Becoming The First confirmation: {e}")
        return {"status": "failed", "email": registration_data['email'], "type": "becoming_first_confirmation", "error": str(e)}


async def notify_admin_new_becoming_first_registration(
    registration_data: dict,
    graph_client: MicrosoftGraphClientPublic,
    admin_emails: list = None
) -> dict:
    """Notify admin team about new Becoming The First registration."""
    
    from app.constants.constants import ADMIN_EMAILS
    if admin_emails is None:
        admin_emails = ADMIN_EMAILS
    
    # Parse fields of interest
    try:
        if isinstance(registration_data['fields_of_interest'], str):
            import json
            interests_list = json.loads(registration_data['fields_of_interest'])
        else:
            interests_list = registration_data['fields_of_interest']
        interests_html = "".join([f'<span style="display:inline-block;padding:5px 12px;border-radius:15px;font-size:12px;font-weight:bold;color:white;background:#0a2463;margin:3px;">{i}</span>' for i in interests_list])
    except:
        interests_html = '<span>Not specified</span>'
    
    email_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: linear-gradient(135deg, #0a2463 0%, #1449c9 100%); color: white; padding: 30px; border-radius: 10px 10px 0 0; }}
            .content {{ background: #f9fafb; padding: 30px; border-radius: 0 0 10px 10px; }}
            .details {{ background: white; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #FFC007; }}
            .detail-row {{ margin: 12px 0; padding: 8px 0; border-bottom: 1px solid #f3f4f6; }}
            .detail-row:last-child {{ border-bottom: none; }}
            .label {{ font-weight: bold; color: #6b7280; font-size: 12px; text-transform: uppercase; }}
            .value {{ color: #1f2937; font-size: 15px; margin-top: 4px; }}
            .priority-badge {{ display: inline-block; padding: 8px 20px; border-radius: 20px; font-size: 14px; font-weight: bold; color: white; background: #FFC007; color: #0a2463; }}
            .text-box {{ background: #dbeafe; padding: 15px; border-radius: 8px; margin: 10px 0; }}
            .stats-box {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; margin: 20px 0; }}
            .stat-item {{ background: white; padding: 15px; border-radius: 8px; text-align: center; border: 1px solid #e5e7eb; }}
            .stat-number {{ font-size: 24px; font-weight: bold; color: #0a2463; }}
            .stat-label {{ font-size: 12px; color: #6b7280; text-transform: uppercase; }}
            h1 {{ margin: 0; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>✨ New Registration: Becoming The First</h1>
            </div>
            <div class="content">
                <div class="priority-badge">🎉 NEW ATTENDEE</div>
                
                <div class="details">
                    <div class="detail-row">
                        <div class="label">Registration ID</div>
                        <div class="value">{registration_id}</div>
                    </div>
                    <div class="detail-row">
                        <div class="label">Full Name</div>
                        <div class="value" style="font-size: 18px; font-weight: bold; color: #0a2463;">{full_name}</div>
                    </div>
                    <div class="detail-row">
                        <div class="label">Email</div>
                        <div class="value"><a href="mailto:{email}" style="color: #1449c9;">{email}</a></div>
                    </div>
                    <div class="detail-row">
                        <div class="label">Phone</div>
                        <div class="value">{contact_number}</div>
                    </div>
                    <div class="detail-row">
                        <div class="label">Location</div>
                        <div class="value">📍 {location}</div>
                    </div>
                    <div class="detail-row">
                        <div class="label">Current Role</div>
                        <div class="value">{current_role}</div>
                    </div>
                    <div class="detail-row">
                        <div class="label">Fields of Interest</div>
                        <div class="value">{fields_of_interest}</div>
                    </div>
                    <div class="detail-row">
                        <div class="label">Referral Source</div>
                        <div class="value">{referral_source}</div>
                    </div>
                    <div class="detail-row">
                        <div class="label">Receive Updates</div>
                        <div class="value">{receive_updates}</div>
                    </div>
                    <div class="detail-row">
                        <div class="label">Registered</div>
                        <div class="value">{submission_date}</div>
                    </div>
                </div>
                
                <div class="text-box">
                    <div class="label">Why They Want to Attend</div>
                    <p style="margin: 8px 0; color: #1f2937;">{why_attend}</p>
                </div>
                
                <div class="text-box">
                    <div class="label">Learning Expectations from Philip's Story</div>
                    <p style="margin: 8px 0; color: #1f2937;">{learning_expectations}</p>
                </div>
                
                <div style="background: #fef3c7; padding: 15px; border-radius: 8px; margin: 20px 0; text-align: center;">
                    <p style="margin: 0; color: #92400e; font-size: 14px;">
                        <strong>📅 Event:</strong> Wednesday, December 10th, 2025 at 7:00 PM GMT<br>
                        <strong>🌐 Platform:</strong> Google Meet (Online)
                    </p>
                </div>
                
                <p style="text-align:center;margin-top:20px;color:#6b7280;font-size:12px;">
                    💡 This attendee has been sent a confirmation email with the meeting link
                </p>
            </div>
        </div>
    </body>
    </html>
    """
    
    try:
        result = await graph_client.send_admin_notification(
            admin_emails=admin_emails,
            subject=f"[Becoming The First] New Registration - {registration_data['full_name']}",
            template_html=email_template,
            template_vars={
                "registration_id": registration_data['registration_id'],
                "full_name": registration_data['full_name'],
                "email": registration_data['email'],
                "contact_number": registration_data.get('contact_number') or 'Not provided',
                "location": registration_data['location'],
                "current_role": registration_data['current_role'],
                "fields_of_interest": interests_html,
                "why_attend": registration_data['why_attend'],
                "learning_expectations": registration_data['learning_expectations'],
                "referral_source": registration_data['referral_source'],
                "receive_updates": "Yes ✅" if registration_data['receive_updates'] else "No",
                "submission_date": registration_data['submitted_at'].strftime("%B %d, %Y at %I:%M %p")
            },
            reply_to_applicant=registration_data['email']
        )
        print(f"✅ Admin notified about Becoming The First registration from {registration_data['full_name']}")
        return {"status": "sent", "type": "admin_becoming_first_notification"}
    except Exception as e:
        print(f"⚠️ Failed to send admin Becoming The First notification: {e}")
        return {"status": "failed", "type": "admin_becoming_first_notification", "error": str(e)}
    
async def notify_axi_launch_registration_confirmation(
    registration_data: dict,
    graph_client: MicrosoftGraphClientPublic
) -> dict:
    """
    Send confirmation email with ticket PDF for AXI Launch registration.
    
    Args:
        registration_data: Dictionary containing:
            - email: str
            - full_name: str
            - registration_id: str
            - qr_code_base64: str
            - event_date: str
            - event_time: str
            - event_location: str
            - submitted_at: datetime
            - ticket_pdf: bytes (optional)
    """
    
    email_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ 
                background: linear-gradient(135deg, #0A2463 0%, #1449c9 100%); 
                color: white; 
                padding: 40px 30px; 
                border-radius: 10px 10px 0 0; 
                text-align: center; 
            }}
            .logo-section {{ margin-bottom: 20px; }}
            .content {{ background: #f9fafb; padding: 30px; border-radius: 0 0 10px 10px; }}
            .event-card {{ 
                background: white; 
                padding: 25px; 
                border-radius: 12px; 
                margin: 20px 0; 
                border-left: 5px solid #FFC007;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }}
            .detail-row {{ 
                margin: 15px 0; 
                display: flex; 
                align-items: start;
                padding: 10px 0;
                border-bottom: 1px solid #f3f4f6;
            }}
            .detail-row:last-child {{ border-bottom: none; }}
            .icon {{ font-size: 24px; margin-right: 12px; min-width: 30px; }}
            .detail-content {{ flex: 1; }}
            .label {{ 
                font-weight: bold; 
                color: #6b7280; 
                font-size: 11px; 
                text-transform: uppercase; 
                letter-spacing: 0.5px; 
            }}
            .value {{ color: #1f2937; font-size: 16px; margin-top: 4px; }}
            .status-badge {{ 
                display: inline-block; 
                padding: 12px 30px; 
                border-radius: 25px; 
                font-size: 14px; 
                font-weight: bold; 
                color: white; 
                background: #10b981; 
                margin: 20px 0; 
            }}
            .qr-code-section {{ 
                background: linear-gradient(135deg, #f9fafb 0%, #ffffff 100%);
                padding: 25px; 
                border-radius: 12px; 
                margin: 25px 0; 
                text-align: center;
                border: 2px dashed #e5e7eb;
            }}
            .qr-code-img {{ 
                max-width: 250px; 
                height: auto; 
                margin: 15px auto;
                display: block;
                border: 3px solid #0A2463;
                border-radius: 8px;
                padding: 10px;
                background: white;
            }}
            .important-box {{ 
                background: #fef3c7; 
                border-left: 4px solid #FFC007; 
                padding: 20px; 
                border-radius: 8px; 
                margin: 20px 0; 
            }}
            .cta-button {{ 
                display: inline-block; 
                padding: 15px 40px; 
                background: #0A2463; 
                color: white; 
                text-decoration: none; 
                border-radius: 8px; 
                font-weight: bold; 
                font-size: 16px; 
                margin: 15px 0;
                transition: transform 0.2s;
            }}
            .cta-button:hover {{ transform: translateY(-2px); }}
            .benefits-list {{ 
                background: white; 
                padding: 20px 25px; 
                border-radius: 8px; 
                margin: 20px 0; 
            }}
            .benefits-list li {{ 
                margin: 12px 0; 
                padding-left: 10px;
                color: #4b5563;
            }}
            .footer {{ 
                text-align: center; 
                margin-top: 30px; 
                color: #6b7280; 
                font-size: 12px; 
                padding-top: 20px; 
                border-top: 1px solid #e5e7eb; 
            }}
            h1 {{ margin: 0; font-size: 36px; text-shadow: 2px 2px 4px rgba(0,0,0,0.2); }}
            h2 {{ color: #0A2463; font-size: 24px; margin-top: 0; }}
            h3 {{ color: #0A2463; font-size: 20px; margin-top: 0; }}
            .emoji {{ font-size: 56px; margin: 15px 0; }}
            .highlight {{ color: #FFC007; font-weight: bold; }}
            .registration-id {{ 
                font-family: 'Courier New', monospace; 
                font-size: 13px; 
                color: #6b7280;
                background: #f3f4f6;
                padding: 8px 12px;
                border-radius: 4px;
                display: inline-block;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div class="emoji">🚀</div>
                <h1>Welcome to AXI LAUNCH!</h1>
                <p style="margin: 15px 0 0 0; font-size: 18px; opacity: 0.95;">
                    Your Journey to Innovation Starts Here
                </p>
            </div>
            
            <div class="content">
                <p style="font-size: 16px;">Hi <strong>{full_name}</strong>,</p>
                
                <p style="font-size: 15px; line-height: 1.8;">
                    🎉 Congratulations! You're officially registered for <strong class="highlight">AXI Launch 2026</strong> 
                    — Ghana's premier startup and innovation event. Get ready to connect with founders, investors, 
                    builders, and changemakers who are shaping Africa's future!
                </p>
                
                <div style="text-align: center;">
                    <div class="status-badge">✓ REGISTRATION CONFIRMED</div>
                </div>
                
                <div class="event-card">
                    <h2>📅 Event Details</h2>
                    
                    <div class="detail-row">
                        <div class="icon">🎯</div>
                        <div class="detail-content">
                            <div class="label">Event</div>
                            <div class="value">AXI Launch 2025</div>
                        </div>
                    </div>
                    
                    <div class="detail-row">
                        <div class="icon">📆</div>
                        <div class="detail-content">
                            <div class="label">Date</div>
                            <div class="value">{event_date}</div>
                        </div>
                    </div>
                    
                    <div class="detail-row">
                        <div class="icon">🕐</div>
                        <div class="detail-content">
                            <div class="label">Time</div>
                            <div class="value">{event_time}</div>
                        </div>
                    </div>
                    
                    <div class="detail-row">
                        <div class="icon">📍</div>
                        <div class="detail-content">
                            <div class="label">Location</div>
                            <div class="value">{event_location}</div>
                        </div>
                    </div>
                    
                    <div class="detail-row">
                        <div class="icon">🎫</div>
                        <div class="detail-content">
                            <div class="label">Registration ID</div>
                            <div class="registration-id">{registration_id}</div>
                        </div>
                    </div>
                </div>
            
                <div class="important-box">
                    <strong style="font-size: 16px; color: #92400e;">📎 Your Ticket is Attached!</strong>
                    <p style="margin: 12px 0 0 0; font-size: 14px; color: #78350f;">
                        We've attached your official AXI Launch ticket as a PDF. You can print it or 
                        save it on your phone for easy access at the event.
                    </p>
                </div>
                
                <div style="text-align: center; margin: 35px 0; padding: 25px; background: linear-gradient(135deg, #0A2463 0%, #1449c9 100%); border-radius: 12px;">
                    <p style="font-size: 20px; color: white; font-weight: bold; margin: 0 0 10px 0;">
                        🎯 Prepare to Launch Your Future!
                    </p>
                    <p style="color: rgba(255,255,255,0.9); font-size: 14px; margin: 0;">
                        Join hundreds of innovators, builders, and dreamers at Ghana's biggest startup event
                    </p>
                </div>
                
                
                <div style="text-align: center; margin: 30px 0;">
                    <p style="font-size: 16px; color: #4b5563;">
                        Questions? We're here to help!
                    </p>
                    <p style="color: #6b7280; font-size: 14px; margin-top: 10px;">
                        Reply to this email or contact us at 
                        <a href="mailto:axi@ideationaxis.com" style="color: #0A2463; font-weight: bold;">
                            axi@ideationaxis.com
                        </a>
                    </p>
                </div>
                
                <div class="footer">
                    <p style="font-size: 14px; margin-bottom: 10px;">
                        <strong style="color: #0A2463;">IDEATION AXIS GROUP</strong>
                    </p>
                    <p style="margin: 5px 0;">Africa's Startup Engine</p>
                    <p style="margin: 5px 0;">Building The Future • Empowering Innovation</p>
                    <p style="margin: 15px 0 5px 0;">
                        <a href="https://ideationaxis.com" style="color: #0A2463; text-decoration: none;">
                            ideationaxis.com
                        </a>
                    </p>
                    <p style="font-size: 11px; color: #9ca3af; margin-top: 20px;">
                        © 2025 Ideation Axis Group. All rights reserved.
                    </p>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    
    # Prepare attachments
    attachments = []
    if registration_data.get('ticket_pdf'):
        try:
            pdf_base64 = base64.b64encode(registration_data['ticket_pdf']).decode()
            attachments.append({
                "@odata.type": "#microsoft.graph.fileAttachment",
                "name": f"AXI_Launch_Ticket_{registration_data['registration_id'][:8]}.pdf",
                "contentType": "application/pdf",
                "contentBytes": pdf_base64
            })
        except Exception as e:
            print(f"Error preparing PDF attachment: {e}")
    
    try:
        result = await graph_client.send_email(
            to_emails=[registration_data['email']],
            subject="🚀 You're Registered for AXI Launch 2025! Your Ticket Inside",
            body_html=email_template.format(
                full_name=registration_data['full_name'],
                registration_id=registration_data['registration_id'],
                event_date=registration_data['event_date'],
                event_time=registration_data['event_time'],
                event_location=registration_data['event_location'],
                qr_code_base64=registration_data.get('qr_code_base64', ''),
                submission_date=registration_data['submitted_at'].strftime("%B %d, %Y at %I:%M %p")
            ),
            department="events",
            attachments=attachments if attachments else None
        )
        
        print(f"✅ AXI Launch confirmation email sent to {registration_data['email']}")
        return {
            "status": "sent", 
            "email": registration_data['email'], 
            "type": "axi_launch_confirmation",
            "attachments": len(attachments)
        }
    
    except Exception as e:
        print(f"⚠️ Failed to send AXI Launch confirmation: {e}")
        return {
            "status": "failed", 
            "email": registration_data['email'], 
            "type": "axi_launch_confirmation", 
            "error": str(e)
        }


async def notify_admin_new_axi_launch_registration(
    registration_data: dict,
    graph_client: MicrosoftGraphClientPublic,
    admin_emails: list = None
) -> dict:
    """
    Notify admin team about new AXI Launch registration.
    
    Args:
        registration_data: Dictionary containing all registration details
        graph_client: Microsoft Graph client
        admin_emails: List of admin email addresses
    """
    
    from app.constants.constants import ADMIN_EMAILS
    if admin_emails is None:
        admin_emails = ADMIN_EMAILS
    
    # Build role-specific details HTML
    role_details = ""
    if registration_data.get('current_role_other'):
        role_details += f"<div class='detail-row'><div class='label'>Other Role</div><div class='value'>{registration_data['current_role_other']}</div></div>"
    
    if registration_data.get('builder_type'):
        role_details += f"<div class='detail-row'><div class='label'>Developer Type</div><div class='value'>{registration_data['builder_type']}</div></div>"
    
    if registration_data.get('builder_type_other'):
        role_details += f"<div class='detail-row'><div class='label'>Other Developer Type</div><div class='value'>{registration_data['builder_type_other']}</div></div>"
    
    if registration_data.get('experience_level'):
        role_details += f"<div class='detail-row'><div class='label'>Experience Level</div><div class='value'>{registration_data['experience_level']}</div></div>"
    
    if registration_data.get('startup_stage'):
        role_details += f"<div class='detail-row'><div class='label'>Startup Stage</div><div class='value'>{registration_data['startup_stage']}</div></div>"
    
    if registration_data.get('startup_name'):
        role_details += f"<div class='detail-row'><div class='label'>Startup Name</div><div class='value'><strong>{registration_data['startup_name']}</strong></div></div>"
    
    if registration_data.get('investor_type'):
        role_details += f"<div class='detail-row'><div class='label'>Investor Type</div><div class='value'>{registration_data['investor_type']}</div></div>"
    
    if registration_data.get('investment_focus'):
        role_details += f"<div class='detail-row'><div class='label'>Investment Focus</div><div class='value'>{registration_data['investment_focus']}</div></div>"
    
    if registration_data.get('expertise_areas'):
        role_details += f"<div class='detail-row'><div class='label'>Expertise Areas</div><div class='value'>{registration_data['expertise_areas']}</div></div>"
    
    if registration_data.get('organization_name'):
        role_details += f"<div class='detail-row'><div class='label'>Organization</div><div class='value'>{registration_data['organization_name']}</div></div>"
    
    email_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 700px; margin: 0 auto; padding: 20px; }}
            .header {{ 
                background: linear-gradient(135deg, #0A2463 0%, #1449c9 100%); 
                color: white; 
                padding: 30px; 
                border-radius: 10px 10px 0 0; 
            }}
            .content {{ background: #f9fafb; padding: 30px; border-radius: 0 0 10px 10px; }}
            .details {{ 
                background: white; 
                padding: 20px; 
                border-radius: 8px; 
                margin: 20px 0; 
                border-left: 5px solid #FFC007; 
            }}
            .detail-row {{ 
                margin: 12px 0; 
                padding: 10px 0; 
                border-bottom: 1px solid #f3f4f6; 
            }}
            .detail-row:last-child {{ border-bottom: none; }}
            .label {{ 
                font-weight: bold; 
                color: #6b7280; 
                font-size: 11px; 
                text-transform: uppercase; 
                letter-spacing: 0.5px;
            }}
            .value {{ color: #1f2937; font-size: 15px; margin-top: 4px; }}
            .priority-badge {{ 
                display: inline-block; 
                padding: 10px 24px; 
                border-radius: 20px; 
                font-size: 14px; 
                font-weight: bold; 
                color: #0A2463; 
                background: #FFC007; 
            }}
            .text-box {{ 
                background: #dbeafe; 
                padding: 18px; 
                border-radius: 8px; 
                margin: 15px 0; 
                border-left: 4px solid #0A2463;
            }}
            .highlight {{ color: #0A2463; font-weight: bold; }}
            h1 {{ margin: 0; font-size: 28px; }}
            h3 {{ color: #0A2463; margin-top: 0; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🚀 New AXI Launch Registration</h1>
                <p style="margin: 10px 0 0 0; opacity: 0.9;">A new attendee has registered for the event!</p>
            </div>
            
            <div class="content">
                <div style="text-align: center; margin-bottom: 20px;">
                    <div class="priority-badge">🎉 NEW ATTENDEE</div>
                </div>
                
                <div class="details">
                    <h3>👤 Personal Information</h3>
                    
                    <div class="detail-row">
                        <div class="label">Registration ID</div>
                        <div class="value" style="font-family: 'Courier New', monospace; font-size: 13px; color: #6b7280;">{registration_id}</div>
                    </div>
                    
                    <div class="detail-row">
                        <div class="label">Full Name</div>
                        <div class="value" style="font-size: 18px; font-weight: bold; color: #0A2463;">{full_name}</div>
                    </div>
                    
                    <div class="detail-row">
                        <div class="label">Email</div>
                        <div class="value">
                            <a href="mailto:{email}" style="color: #1449c9; text-decoration: none;">{email}</a>
                        </div>
                    </div>
                    
                    <div class="detail-row">
                        <div class="label">Phone</div>
                        <div class="value">{contact_number}</div>
                    </div>
                    
                    <div class="detail-row">
                        <div class="label">Location</div>
                        <div class="value">📍 {location}</div>
                    </div>
                </div>
                
                <div class="details">
                    <h3>💼 Professional Background</h3>
                    
                    <div class="detail-row">
                        <div class="label">Current Role</div>
                        <div class="value"><strong>{current_role}</strong></div>
                    </div>
                    
                    {role_details}
                </div>
                
                <div class="text-box">
                    <div class="label">Why They Want to Attend</div>
                    <p style="margin: 10px 0 0 0; color: #1f2937; font-size: 14px;">{why_attend}</p>
                </div>
                
                <div class="text-box">
                    <div class="label">Networking Goals</div>
                    <p style="margin: 10px 0 0 0; color: #1f2937; font-size: 14px;">{networking_goals}</p>
                </div>
                
                <div class="details">
                    <h3>📊 Additional Information</h3>
                    
                    <div class="detail-row">
                        <div class="label">Referral Source</div>
                        <div class="value">{referral_source}</div>
                    </div>
                    
                    <div class="detail-row">
                        <div class="label">Receive Updates</div>
                        <div class="value">{receive_updates}</div>
                    </div>
                    
                    <div class="detail-row">
                        <div class="label">Registered At</div>
                        <div class="value">{submission_date}</div>
                    </div>
                </div>
                
                <div style="background: #fef3c7; padding: 18px; border-radius: 8px; margin: 20px 0; text-align: center;">
                    <p style="margin: 0; color: #92400e; font-size: 14px;">
                        ✅ <strong>Confirmation email with ticket has been sent to the attendee</strong>
                    </p>
                </div>
                
                <div style="text-align: center; margin-top: 25px; padding-top: 20px; border-top: 1px solid #e5e7eb;">
                    <p style="color: #6b7280; font-size: 12px; margin: 0;">
                        <strong>Ideation Axis Group</strong> • AXI Launch 2025<br>
                        Event Management System
                    </p>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    
    try:
        result = await graph_client.send_email(
            to_emails=admin_emails,
            subject=f"[AXI Launch] New Registration - {registration_data['full_name']} ({registration_data['current_role']})",
            body_html=email_template.format(
                registration_id=registration_data['registration_id'],
                full_name=registration_data['full_name'],
                email=registration_data['email'],
                contact_number=registration_data.get('contact_number') or 'Not provided',
                location=registration_data['location'],
                current_role=registration_data['current_role'],
                role_details=role_details,
                why_attend=registration_data['why_attend'],
                networking_goals=registration_data['networking_goals'],
                referral_source=registration_data['referral_source'],
                receive_updates="Yes ✅" if registration_data['receive_updates'] else "No",
                submission_date=registration_data['submitted_at'].strftime("%B %d, %Y at %I:%M %p")
            ),
            department="events",
            reply_to=registration_data['email']
        )
        
        print(f"✅ Admin notified about AXI Launch registration from {registration_data['full_name']}")
        return {
            "status": "sent", 
            "type": "admin_axi_launch_notification",
            "recipients": len(admin_emails)
        }
    
    except Exception as e:
        print(f"⚠️ Failed to send admin AXI Launch notification: {e}")
        return {
            "status": "failed", 
            "type": "admin_axi_launch_notification", 
            "error": str(e)
        }
    
async def notify_job_application_received(
    application_data: dict,
    graph_client: MicrosoftGraphClientPublic
) -> dict:
    """Send confirmation email for job application."""
    
    email_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: linear-gradient(135deg, #0A2463 0%, #1e40af 100%); color: white; padding: 30px; border-radius: 10px 10px 0 0; text-align: center; }}
            .content {{ background: #f9fafb; padding: 30px; border-radius: 0 0 10px 10px; }}
            .application-details {{ background: white; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #FFC007; }}
            .detail-row {{ margin: 10px 0; }}
            .label {{ font-weight: bold; color: #6b7280; }}
            .value {{ color: #1f2937; }}
            .status-badge {{ display: inline-block; padding: 8px 20px; border-radius: 20px; font-size: 14px; font-weight: bold; color: white; background: #10b981; margin: 15px 0; }}
            .footer {{ text-align: center; margin-top: 20px; color: #6b7280; font-size: 12px; }}
            .cta-button {{ display: inline-block; padding: 12px 30px; background: #FFC007; color: #0A2463; text-decoration: none; border-radius: 6px; font-weight: bold; margin-top: 20px; }}
            h1 {{ margin: 0; font-size: 32px; }}
            h3 {{ margin-top: 0; color: #0A2463; }}
            .emoji {{ font-size: 48px; margin: 10px 0; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div class="emoji">🎯</div>
                <h1>Application Received!</h1>
            </div>
            <div class="content">
                <p>Hi <strong>{full_name}</strong>,</p>
                <p>Thank you for applying to the <strong>{job_title}</strong> position at Ideation Axis Group!</p>
                
                <div style="text-align: center;">
                    <div class="status-badge">✓ APPLICATION RECEIVED</div>
                </div>
                
                <div class="application-details">
                    <h3>📋 Application Summary</h3>
                    <div class="detail-row">
                        <span class="label">Position:</span><br>
                        <span class="value">{job_title}</span>
                    </div>
                    <div class="detail-row">
                        <span class="label">Application ID:</span><br>
                        <span class="value">{application_id}</span>
                    </div>
                    <div class="detail-row">
                        <span class="label">Submitted:</span><br>
                        <span class="value">{submission_date}</span>
                    </div>
                </div>
                
                <p><strong>What happens next?</strong></p>
                <ul>
                    <li>Our hiring team will carefully review your application</li>
                    <li>If your profile matches our requirements, we'll reach out within 1-2 weeks</li>
                    <li>You'll receive updates via email at {email}</li>
                    <li>We review all applications thoroughly, so please be patient</li>
                </ul>
                
                <div style="background: #fef3c7; padding: 15px; border-radius: 8px; margin: 20px 0;">
                    <strong>💡 In the meantime:</strong>
                    <ul style="margin: 10px 0;">
                        <li>Follow us on social media to stay updated</li>
                        <li>Check out our other open positions</li>
                        <li>Learn more about our company culture</li>
                    </ul>
                </div>
                
                <div style="text-align: center;">
                    <a href="https://ideationaxis.com/careers" class="cta-button">View Open Positions</a>
                </div>
                
                <div class="footer">
                    <p>Thank you for your interest in joining Ideation Axis Group!</p>
                    <p>Best regards,<br>The Ideation Axis Group Careers Team</p>
                    <p style="margin-top: 20px;">
                        <strong>Ideation Axis Group</strong><br>
                        Africa's Startup Engine<br>
                        <a href="https://ideationaxis.com" style="color: #0A2463;">ideationaxis.com</a>
                    </p>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    
    try:
        result = await graph_client.send_user_confirmation(
            to_email=application_data['email'],
            subject=f"Application Received - {application_data['job_title']}",
            template_html=email_template,
            template_vars={
                "full_name": application_data['full_name'],
                "job_title": application_data['job_title'],
                "application_id": application_data['application_id'],
                "submission_date": application_data['submitted_at'].strftime("%B %d, %Y at %I:%M %p"),
                "email": application_data['email']
            },
            department="careers"
        )
        print(f"✅ Job application confirmation sent to {application_data['email']}")
        return {"status": "sent", "email": application_data['email'], "type": "job_application_confirmation"}
    except Exception as e:
        print(f"⚠️ Failed to send job application confirmation: {e}")
        return {"status": "failed", "email": application_data['email'], "type": "job_application_confirmation", "error": str(e)}


async def notify_admin_new_job_application(
    application_data: dict,
    graph_client: MicrosoftGraphClientPublic,
    admin_emails: list = None
) -> dict:
    """Notify admin team about new job application."""
    
    from app.constants.constants import ADMIN_EMAILS
    if admin_emails is None:
        admin_emails = ADMIN_EMAILS
    
    email_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 700px; margin: 0 auto; padding: 20px; }}
            .header {{ background: linear-gradient(135deg, #0A2463 0%, #1449c9 100%); color: white; padding: 30px; border-radius: 10px 10px 0 0; }}
            .content {{ background: #f9fafb; padding: 30px; border-radius: 0 0 10px 10px; }}
            .details {{ background: white; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #FFC007; }}
            .detail-row {{ margin: 12px 0; padding: 8px 0; border-bottom: 1px solid #f3f4f6; }}
            .detail-row:last-child {{ border-bottom: none; }}
            .label {{ font-weight: bold; color: #6b7280; font-size: 12px; text-transform: uppercase; }}
            .value {{ color: #1f2937; font-size: 15px; margin-top: 4px; }}
            .priority-badge {{ display: inline-block; padding: 8px 20px; border-radius: 20px; font-size: 14px; font-weight: bold; color: #0A2463; background: #FFC007; }}
            .text-box {{ background: #dbeafe; padding: 15px; border-radius: 8px; margin: 10px 0; }}
            h1 {{ margin: 0; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🎯 New Job Application</h1>
            </div>
            <div class="content">
                <div class="priority-badge">NEW CANDIDATE</div>
                
                <div class="details">
                    <div class="detail-row">
                        <div class="label">Application ID</div>
                        <div class="value">{application_id}</div>
                    </div>
                    <div class="detail-row">
                        <div class="label">Position</div>
                        <div class="value" style="font-weight:bold;color:#0A2463;font-size:18px;">{job_title}</div>
                    </div>
                    <div class="detail-row">
                        <div class="label">Applicant Name</div>
                        <div class="value">{full_name}</div>
                    </div>
                    <div class="detail-row">
                        <div class="label">Email</div>
                        <div class="value"><a href="mailto:{email}">{email}</a></div>
                    </div>
                    <div class="detail-row">
                        <div class="label">Phone</div>
                        <div class="value">{phone_number}</div>
                    </div>
                    <div class="detail-row">
                        <div class="label">LinkedIn</div>
                        <div class="value">{linkedin_url}</div>
                    </div>
                    <div class="detail-row">
                        <div class="label">Portfolio</div>
                        <div class="value">{portfolio_url}</div>
                    </div>
                    <div class="detail-row">
                        <div class="label">Submitted</div>
                        <div class="value">{submission_date}</div>
                    </div>
                </div>
                
                <div class="text-box">
                    <div class="label">Why They're a Good Fit</div>
                    <p>{why_fit}</p>
                </div>
                
                <div class="text-box">
                    <div class="label">Cover Letter</div>
                    <p>{cover_letter}</p>
                </div>
                
                <div style="background: #fef3c7; padding: 15px; border-radius: 8px; margin: 20px 0; text-align: center;">
                    <p style="margin: 0; color: #92400e; font-size: 14px;">
                        📊 <strong>Review this application in the admin panel</strong>
                    </p>
                </div>
                
                <p style="text-align:center;margin-top:20px;color:#6b7280;font-size:12px;">
                    💡 Click Reply to respond directly to the applicant
                </p>
            </div>
        </div>
    </body>
    </html>
    """
    
    try:
        result = await graph_client.send_admin_notification(
            admin_emails=admin_emails,
            subject=f"[Job Application] {application_data['job_title']} - {application_data['full_name']}",
            template_html=email_template,
            template_vars={
                "application_id": application_data['application_id'],
                "job_title": application_data['job_title'],
                "full_name": application_data['full_name'],
                "email": application_data['email'],
                "phone_number": application_data.get('phone_number') or 'Not provided',
                "linkedin_url": application_data.get('linkedin_url') or 'Not provided',
                "portfolio_url": application_data.get('portfolio_url') or 'Not provided',
                "why_fit": application_data['why_fit'],
                "cover_letter": application_data.get('cover_letter') or 'Not provided',
                "submission_date": application_data['submitted_at'].strftime("%B %d, %Y at %I:%M %p")
            },
            reply_to_applicant=application_data['email']
        )
        print(f"✅ Admin notified about job application from {application_data['full_name']}")
        return {"status": "sent", "type": "admin_job_application_notification"}
    except Exception as e:
        print(f"⚠️ Failed to send admin job application notification: {e}")
        return {"status": "failed", "type": "admin_job_application_notification", "error": str(e)}
    
"""
Add this function to your app/services/EventApplicationConfirmationEmail.py file
"""

async def notify_waitlisters_new_job(
    job_data: dict,
    waitlister_data: dict,
    graph_client: MicrosoftGraphClientPublic
) -> dict:
    """
    Notify a job waitlister about a new job opening that matches their interest.
    
    Args:
        job_data: Dictionary containing job details (job_id, title, description, etc.)
        waitlister_data: Dictionary containing waitlister details (email, full_name, etc.)
        graph_client: Microsoft Graph client instance
    """
    
    email_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ 
                background: linear-gradient(135deg, #0A2463 0%, #1e40af 100%); 
                color: white; 
                padding: 35px 30px; 
                border-radius: 10px 10px 0 0; 
                text-align: center;
            }}
            .content {{ background: #f9fafb; padding: 30px; border-radius: 0 0 10px 10px; }}
            .job-card {{ 
                background: white; 
                padding: 25px; 
                border-radius: 12px; 
                margin: 20px 0; 
                border-left: 5px solid #FFC007;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }}
            .detail-row {{ margin: 15px 0; display: flex; align-items: start; }}
            .icon {{ font-size: 20px; margin-right: 12px; min-width: 25px; }}
            .detail-content {{ flex: 1; }}
            .label {{ font-weight: bold; color: #6b7280; font-size: 12px; text-transform: uppercase; }}
            .value {{ color: #1f2937; font-size: 15px; margin-top: 4px; }}
            .status-badge {{ 
                display: inline-block; 
                padding: 10px 25px; 
                border-radius: 25px; 
                font-size: 14px; 
                font-weight: bold; 
                color: white; 
                background: #10b981; 
                margin: 15px 0; 
            }}
            .cta-button {{ 
                display: inline-block; 
                padding: 15px 40px; 
                background: #FFC007; 
                color: #0A2463; 
                text-decoration: none; 
                border-radius: 8px; 
                font-weight: bold; 
                font-size: 16px;
                margin-top: 20px;
                transition: transform 0.2s;
            }}
            .cta-button:hover {{ transform: translateY(-2px); }}
            .tags {{ margin: 15px 0; }}
            .tag {{ 
                display: inline-block; 
                padding: 5px 12px; 
                background: #dbeafe; 
                color: #1e40af; 
                border-radius: 15px; 
                font-size: 12px; 
                font-weight: bold; 
                margin: 3px; 
            }}
            .footer {{ text-align: center; margin-top: 30px; color: #6b7280; font-size: 12px; padding-top: 20px; border-top: 1px solid #e5e7eb; }}
            .highlight-box {{ 
                background: #fef3c7; 
                border-left: 4px solid #FFC007; 
                padding: 15px; 
                border-radius: 6px; 
                margin: 20px 0; 
            }}
            h1 {{ margin: 0; font-size: 32px; }}
            h2 {{ color: #0A2463; font-size: 24px; margin-top: 0; }}
            .emoji {{ font-size: 48px; margin: 10px 0; }}
            ul {{ margin: 10px 0; padding-left: 20px; }}
            li {{ margin: 8px 0; color: #4b5563; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div class="emoji">🎉</div>
                <h1>New Job Opening!</h1>
                <p style="margin: 10px 0 0 0; font-size: 18px; opacity: 0.95;">
                    A position matching your interests is now available
                </p>
            </div>
            
            <div class="content">
                <p>Hi <strong>{full_name}</strong>,</p>
                
                <p style="font-size: 16px;">
                    Great news! We have a new job opening that might be perfect for you. 
                    You're receiving this because you joined our job waitlist for <strong>{preferred_role}</strong> positions.
                </p>
                
                <div style="text-align: center;">
                    <div class="status-badge">✨ NEW OPPORTUNITY</div>
                </div>
                
                <div class="job-card">
                    <h2>💼 {job_title}</h2>
                    
                    <div class="detail-row">
                        <div class="icon">📍</div>
                        <div class="detail-content">
                            <div class="label">Location</div>
                            <div class="value">{location}</div>
                        </div>
                    </div>
                    
                    <div class="detail-row">
                        <div class="icon">💰</div>
                        <div class="detail-content">
                            <div class="label">Employment Type</div>
                            <div class="value">{employment_type}</div>
                        </div>
                    </div>
                    
                    <div class="detail-row">
                        <div class="icon">📊</div>
                        <div class="detail-content">
                            <div class="label">Experience Level</div>
                            <div class="value">{experience_level}</div>
                        </div>
                    </div>
                    
                    {salary_range_html}
                    
                    <div class="tags">
                        {tags_html}
                    </div>
                    
                    <div style="margin-top: 20px;">
                        <div class="label">About the Role</div>
                        <p style="color: #4b5563; margin-top: 8px;">{description_preview}</p>
                    </div>
                </div>
                
                <div class="highlight-box">
                    <strong>⚡ Act Fast!</strong>
                    <p style="margin: 8px 0 0 0; color: #92400e; font-size: 14px;">
                        This is a competitive opportunity. We encourage you to apply as soon as possible!
                    </p>
                </div>
                
                <div style="background: white; padding: 20px; border-radius: 8px; margin: 20px 0;">
                    <h3 style="margin-top: 0; color: #0A2463; font-size: 18px;">🚀 Why Join Ideation Axis Group?</h3>
                    <ul>
                        <li><strong>Ownership from Day One:</strong> Take charge of meaningful projects</li>
                        <li><strong>Build Real Companies:</strong> Work on ventures that matter</li>
                        <li><strong>Results Over Credentials:</strong> Your work speaks for itself</li>
                        <li><strong>Growth Opportunity:</strong> Fast-track your career in Africa's startup ecosystem</li>
                    </ul>
                </div>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="https://ideationaxis.com/careers" class="cta-button">
                        Apply Now →
                    </a>
                </div>
                
                <div style="background: #f3f4f6; padding: 15px; border-radius: 8px; margin: 20px 0; font-size: 13px; color: #6b7280;">
                    <strong>📌 Note:</strong> You're receiving this email because you signed up for our job waitlist. 
                    <a href="{unsubscribe_url}" style="color: #0A2463;">Click here</a> if you'd like to be removed from the waitlist.
                </div>
                
                <div class="footer">
                    <p><strong>Ideation Axis Group</strong><br>
                    Africa's Startup Engine<br>
                    <a href="https://ideationaxis.com/careers" style="color: #0A2463;">ideationaxis.com/careers</a></p>
                    <p style="margin-top: 15px; font-size: 11px;">
                        © 2025 Ideation Axis Group. All rights reserved.
                    </p>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    
    # Build tags HTML
    try:
        import json
        tags_list = json.loads(job_data.get('tags', '[]')) if isinstance(job_data.get('tags'), str) else job_data.get('tags', [])
        tags_html = "".join([f'<span class="tag">{tag}</span>' for tag in tags_list])
    except:
        tags_html = ""
    
    # Build salary range HTML if provided
    salary_range_html = ""
    if job_data.get('salary_range'):
        salary_range_html = f"""
        <div class="detail-row">
            <div class="icon">💵</div>
            <div class="detail-content">
                <div class="label">Salary Range</div>
                <div class="value">{job_data['salary_range']}</div>
            </div>
        </div>
        """
    
    # Truncate description for preview
    description = job_data.get('description', '')
    description_preview = description[:200] + "..." if len(description) > 200 else description
    
    # Build URLs
    from app.core.config import settings
    job_url = f"{settings.FRONTEND_URL}/careers/jobs/{job_data['job_id']}"
    apply_url = f"{settings.FRONTEND_URL}/careers/jobs/{job_data['job_id']}/apply"
    unsubscribe_url = f"{settings.FRONTEND_URL}/careers/waitlist/unsubscribe?email={waitlister_data['email']}"
    
    try:
        result = await graph_client.send_email(
            to_emails=[waitlister_data['email']],
            subject=f"New Opening: {job_data['title']} at Ideation Axis Group 🎉",
            body_html=email_template.format(
                full_name=waitlister_data['full_name'],
                preferred_role=waitlister_data['preferred_role'],
                job_title=job_data['title'],
                location=job_data.get('location', 'Remote'),
                employment_type=job_data.get('employment_type', 'Full-time'),
                experience_level=job_data.get('experience_level', 'Not specified'),
                salary_range_html=salary_range_html,
                tags_html=tags_html,
                description_preview=description_preview,
                job_url=job_url,
                apply_url=apply_url,
                unsubscribe_url=unsubscribe_url
            ),
            department="careers"
        )
        
        print(f"✅ Job notification sent to {waitlister_data['email']}")
        return {
            "status": "sent", 
            "email": waitlister_data['email'], 
            "type": "job_waitlist_notification"
        }
    
    except Exception as e:
        print(f"⚠️ Failed to send job notification to {waitlister_data['email']}: {e}")
        return {
            "status": "failed", 
            "email": waitlister_data['email'], 
            "type": "job_waitlist_notification", 
            "error": str(e)
        }