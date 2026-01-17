"""New Year 2026 Email Scheduler for AXI Users."""

import asyncio
from datetime import datetime, timedelta
import pytz
from typing import List, Dict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from app.api.v1.endpoints.eventapplications import get_graph_client
from app.core.database import aget_db
from app.models.axiuser import AxiUser
from app.services.MicrosoftGraphClientPublic import MicrosoftGraphClientPublic

logger = logging.getLogger(__name__)

ACCRA_TIMEZONE = pytz.timezone('Africa/Accra')

# Schedule time: 12:00 AM (midnight) on January 1, 2026
NEW_YEAR_HOUR = 0
NEW_YEAR_MINUTE = 0
NEW_YEAR_DAY = 1
NEW_YEAR_MONTH = 1
NEW_YEAR_YEAR = 2026

# Event details
LAUNCH_DATE = "February 7, 2026"
DAYS_TO_LAUNCH = 37  # From Jan 1 to Feb 7
TICKET_URL = "https://ideationaxis.com/events/event-axi-launch-2026"
VENUE = "University of Ghana, Legon"

# Email tracking flags
NEW_YEAR_EMAIL_SENT_FLAG = "new_year_2026_email_sent"



async def send_onboarded_user_email(
    user: AxiUser,
    graph_client: MicrosoftGraphClientPublic,
    total_onboarded: int
) -> dict:
    """Send New Year email to users who completed onboarding."""
    
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
            .content {{ background: #f9fafb; padding: 30px; border-radius: 0 0 10px 10px; }}
            .celebration-banner {{ 
                background: linear-gradient(135deg, #FFC007 0%, #f59e0b 100%);
                padding: 25px;
                border-radius: 12px;
                margin: 20px 0;
                text-align: center;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            }}
            .countdown-box {{ 
                background: white; 
                padding: 25px; 
                border-radius: 12px; 
                margin: 25px 0; 
                border-left: 5px solid #FFC007;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }}
            .countdown-number {{
                font-size: 48px;
                font-weight: bold;
                color: #0A2463;
                text-align: center;
                margin: 10px 0;
            }}
            .countdown-label {{
                font-size: 18px;
                color: #6b7280;
                text-align: center;
                text-transform: uppercase;
                letter-spacing: 1px;
            }}
            .cta-button {{ 
                display: inline-block; 
                padding: 18px 45px; 
                background: #FFC007; 
                color: #0A2463; 
                text-decoration: none; 
                border-radius: 8px; 
                font-weight: bold; 
                font-size: 18px;
                margin: 20px 0;
                transition: transform 0.2s;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            }}
            .cta-button:hover {{ transform: translateY(-2px); }}
            .stats-box {{
                background: linear-gradient(135deg, #dbeafe 0%, #bfdbfe 100%);
                padding: 20px;
                border-radius: 10px;
                margin: 20px 0;
                text-align: center;
            }}
            .stats-number {{
                font-size: 36px;
                font-weight: bold;
                color: #0A2463;
            }}
            .stats-label {{
                font-size: 14px;
                color: #1e40af;
                margin-top: 5px;
            }}
            .highlight-box {{ 
                background: #fef3c7; 
                border-left: 4px solid #FFC007; 
                padding: 20px; 
                border-radius: 8px; 
                margin: 20px 0; 
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
            h2 {{ color: #0A2463; font-size: 26px; margin-top: 0; }}
            .emoji {{ font-size: 64px; margin: 15px 0; }}
            ul {{ margin: 15px 0; padding-left: 20px; }}
            li {{ margin: 10px 0; color: #4b5563; font-size: 15px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div class="emoji">🎉</div>
                <h1>Happy New Year 2026!</h1>
                <p style="margin: 15px 0 0 0; font-size: 20px; opacity: 0.95;">
                    Welcome to a Year of Innovation & Growth
                </p>
            </div>
            
            <div class="content">
                <p style="font-size: 17px;">Dear <strong>{first_name}</strong>,</p>
                
                <p style="font-size: 16px; line-height: 1.8;">
                    As we step into 2026, the entire <strong>Ideation Axis Group</strong> team wants to wish you 
                    a phenomenal year ahead! 🎊
                </p>
                
                <div class="celebration-banner">
                    <h2 style="color: #0A2463; margin: 0;">Thank You for Being Part of AXI! 🙏</h2>
                    <p style="margin: 15px 0 0 0; color: #1f2937; font-size: 16px;">
                        We're grateful to have you in our community of innovators, builders, and changemakers.
                    </p>
                </div>
                
                <div class="stats-box">
                    <div class="stats-number">{total_onboarded:,}+</div>
                    <div class="stats-label">⚡ USERS ALREADY IN THE ECOSYSTEM</div>
                    <p style="margin: 15px 0 0 0; color: #1e40af; font-size: 14px;">
                        You're part of Africa's fastest-growing startup ecosystem!
                    </p>
                </div>
                
                <div class="countdown-box">
                    <h2 style="text-align: center; color: #0A2463;">🚀 The Countdown Begins!</h2>
                    <div class="countdown-number">{days_to_launch}</div>
                    <div class="countdown-label">Days Until AXI Launch</div>
                    <p style="text-align: center; margin-top: 20px; font-size: 16px; color: #4b5563;">
                        <strong>{launch_date}</strong> • {venue}
                    </p>
                </div>
                
                <div class="highlight-box">
                    <h3 style="margin-top: 0; color: #92400e;">🎫 Secure Your Spot Now!</h3>
                    <p style="margin: 10px 0; color: #78350f; font-size: 15px;">
                        AXI Launch 2026 is Ghana's premier startup and innovation event. Don't miss out on:
                    </p>
                    <ul style="color: #78350f;">
                        <li><strong>Networking</strong> with 500+ founders, investors, and builders</li>
                        <li><strong>Keynote speeches</strong> from industry leaders</li>
                        <li><strong>Startup showcases</strong> and pitch competitions</li>
                        <li><strong>Workshops</strong> on fundraising, product development & scaling</li>
                        <li><strong>Partnership opportunities</strong> and investor meetings</li>
                    </ul>
                </div>
                
                <div style="text-align: center; margin: 35px 0;">
                    <a href="{ticket_url}" class="cta-button">
                        GET YOUR TICKET NOW →
                    </a>
                    <p style="color: #6b7280; font-size: 14px; margin-top: 15px;">
                        Early bird pricing available! Limited slots remaining.
                    </p>
                </div>
                
                <div style="background: white; padding: 25px; border-radius: 10px; margin: 25px 0; border: 2px solid #e5e7eb;">
                    <h3 style="margin-top: 0; color: #0A2463; text-align: center;">💪 Make 2026 Your Breakthrough Year</h3>
                    <p style="text-align: center; color: #4b5563; font-size: 15px; line-height: 1.7;">
                        AXI, is committed to helping you build, scale, and succeed. 
                        Whether you're a founder, builder, investor, or innovator — this is your year to shine!
                    </p>
                </div>
                
                <div style="background: linear-gradient(135deg, #0A2463 0%, #1449c9 100%); padding: 25px; border-radius: 12px; margin: 25px 0; text-align: center;">
                    <p style="font-size: 22px; color: white; font-weight: bold; margin: 0;">
                        Let's Build Africa's Startup Engine Together! 🚀
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
                        </a> • 
                        <a href="{ticket_url}" style="color: #0A2463; text-decoration: none;">
                            AXI Launch Tickets
                        </a>
                    </p>
                    <p style="font-size: 11px; color: #9ca3af; margin-top: 20px;">
                        © 2026 Ideation Axis Group. All rights reserved.
                    </p>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    
    try:
        # Normalize email to lowercase
        email = user.email.lower()
        
        result = await graph_client.send_email(
            to_emails=[email],
            subject="🎉 Happy New Year 2026! See You at AXI Launch in 37 Days! 🚀",
            body_html=email_template.format(
                first_name=user.first_name or "Builder",
                total_onboarded=total_onboarded,
                days_to_launch=DAYS_TO_LAUNCH,
                launch_date=LAUNCH_DATE,
                venue=VENUE,
                ticket_url=TICKET_URL
            ),
            department="general"
        )
        
        logger.info(f"✅ New Year email sent to onboarded user: {email}")
        return {"status": "sent", "email": email, "type": "onboarded"}
    
    except Exception as e:
        logger.error(f"❌ Failed to send email to {user.email}: {e}")
        return {"status": "failed", "email": user.email, "error": str(e)}


async def send_incomplete_onboarding_email(
    user: AxiUser,
    graph_client: MicrosoftGraphClientPublic,
    total_onboarded: int
) -> dict:
    """Send New Year email to users who haven't completed onboarding."""
    
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
            .content {{ background: #f9fafb; padding: 30px; border-radius: 0 0 10px 10px; }}
            .celebration-banner {{ 
                background: linear-gradient(135deg, #FFC007 0%, #f59e0b 100%);
                padding: 25px;
                border-radius: 12px;
                margin: 20px 0;
                text-align: center;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            }}
            .urgency-box {{ 
                background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
                padding: 25px; 
                border-radius: 12px; 
                margin: 25px 0; 
                border-left: 5px solid #f59e0b;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }}
            .countdown-box {{ 
                background: white; 
                padding: 25px; 
                border-radius: 12px; 
                margin: 25px 0; 
                border-left: 5px solid #FFC007;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }}
            .countdown-number {{
                font-size: 48px;
                font-weight: bold;
                color: #dc2626;
                text-align: center;
                margin: 10px 0;
            }}
            .countdown-label {{
                font-size: 18px;
                color: #6b7280;
                text-align: center;
                text-transform: uppercase;
                letter-spacing: 1px;
            }}
            .cta-button {{ 
                display: inline-block; 
                padding: 18px 45px; 
                background: #FFC007; 
                color: #0A2463; 
                text-decoration: none; 
                border-radius: 8px; 
                font-weight: bold; 
                font-size: 18px;
                margin: 20px 0;
                transition: transform 0.2s;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            }}
            .cta-button:hover {{ transform: translateY(-2px); }}
            .secondary-button {{
                display: inline-block;
                padding: 15px 35px;
                background: #0A2463;
                color: white;
                text-decoration: none;
                border-radius: 8px;
                font-weight: bold;
                font-size: 16px;
                margin: 10px;
                transition: transform 0.2s;
            }}
            .secondary-button:hover {{ transform: translateY(-2px); }}
            .stats-box {{
                background: linear-gradient(135deg, #fee2e2 0%, #fecaca 100%);
                padding: 20px;
                border-radius: 10px;
                margin: 20px 0;
                text-align: center;
                border: 2px solid #ef4444;
            }}
            .stats-number {{
                font-size: 42px;
                font-weight: bold;
                color: #dc2626;
            }}
            .stats-label {{
                font-size: 14px;
                color: #991b1b;
                margin-top: 5px;
                font-weight: bold;
            }}
            .benefits-list {{
                background: white;
                padding: 20px 25px;
                border-radius: 10px;
                margin: 20px 0;
            }}
            .benefits-list li {{
                margin: 12px 0;
                padding-left: 10px;
                color: #4b5563;
                font-size: 15px;
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
            h2 {{ color: #0A2463; font-size: 26px; margin-top: 0; }}
            .emoji {{ font-size: 64px; margin: 15px 0; }}
            .highlight {{ color: #dc2626; font-weight: bold; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div class="emoji">🎊</div>
                <h1>Happy New Year 2026!</h1>
                <p style="margin: 15px 0 0 0; font-size: 20px; opacity: 0.95;">
                    Don't Miss Out — Complete Your Journey!
                </p>
            </div>
            
            <div class="content">
                <p style="font-size: 17px;">Hi there! 👋</p>
                
                <p style="font-size: 16px; line-height: 1.8;">
                    Happy New Year from the <strong>Ideation Axis Group</strong> team! 🎉
                </p>
                
                <div class="celebration-banner">
                    <h2 style="color: #0A2463; margin: 0;">We're Excited to Have You!</h2>
                    <p style="margin: 15px 0 0 0; color: #1f2937; font-size: 16px;">
                        You're so close to joining Africa's most vibrant startup ecosystem!
                    </p>
                </div>
                
                <div class="stats-box">
                    <div class="stats-number">{total_onboarded:,}+</div>
                    <div class="stats-label">⚡ USERS ALREADY IN THE ECOSYSTEM </div>
                    <p style="margin: 15px 0 0 0; color: #991b1b; font-size: 15px; font-weight: bold;">
                        Don't be left behind! Complete your profile now.
                    </p>
                </div>
                
                <div class="urgency-box">
                    <h2 style="margin-top: 0; color: #92400e; text-align: center;">⏰ Your Profile is Incomplete!</h2>
                    <p style="margin: 15px 0; color: #78350f; font-size: 16px; text-align: center;">
                        You started your journey with AXI, but you haven't finished setting up your profile. 
                        <strong>Complete it now to unlock exclusive opportunities!</strong>
                    </p>
                    <div style="text-align: center; margin-top: 25px;">
                        <a href="https://axi.ideationaxis.com/axi/onboarding" class="cta-button">
                            COMPLETE YOUR PROFILE NOW →
                        </a>
                    </div>
                </div>
                
                <div class="countdown-box">
                    <h2 style="text-align: center; color: #0A2463;">🚀 AXI Launch 2026 is Coming!</h2>
                    <div class="countdown-number">{days_to_launch}</div>
                    <div class="countdown-label">Days Until Launch</div>
                    <p style="text-align: center; margin-top: 20px; font-size: 16px; color: #4b5563;">
                        <strong>{launch_date}</strong> • {venue}
                    </p>
                    <p style="text-align: center; color: #6b7280; font-size: 14px; margin-top: 10px;">
                        Complete your profile and secure your spot at Ghana's biggest startup event!
                    </p>
                </div>
                
                <div class="benefits-list">
                    <h3 style="margin-top: 0; color: #0A2463;">✨ What You Get When You Complete Your Profile:</h3>
                    <ul>
                        <li>🎯 <strong>Access to exclusive opportunities</strong> in the AXI ecosystem</li>
                        <li>🤝 <strong>Connect with 3,000+ builders, founders & investors</strong></li>
                        <li>💼 <strong>Get matched with startups</strong> looking for your skills</li>
                        <li>📢 <strong>Priority access to AXI Launch</strong> and future events</li>
                        <li>🚀 <strong>Showcase your portfolio</strong> to potential collaborators</li>
                        <li>💰 <strong>Investment and partnership opportunities</strong></li>
                    </ul>
                </div>
                
                <div style="background: #fef3c7; padding: 20px; border-radius: 10px; border-left: 4px solid #f59e0b; margin: 25px 0;">
                    <h3 style="margin-top: 0; color: #92400e;">🎫 Don't Miss AXI Launch 2026!</h3>
                    <p style="color: #78350f; font-size: 15px; line-height: 1.7;">
                        Whether you complete your profile or not, you're welcome to attend AXI Launch! 
                        Join 500+ innovators for networking, workshops, and pitch competitions.
                    </p>
                    <div style="text-align: center; margin-top: 20px;">
                        <a href="{ticket_url}" class="secondary-button">
                            GET YOUR TICKET →
                        </a>
                    </div>
                </div>
                
                <div style="background: linear-gradient(135deg, #0A2463 0%, #1449c9 100%); padding: 25px; border-radius: 12px; margin: 25px 0; text-align: center;">
                    <p style="font-size: 24px; color: white; font-weight: bold; margin: 0 0 15px 0;">
                        Make 2026 Your Breakthrough Year! 💪
                    </p>
                    <p style="font-size: 16px; color: rgba(255,255,255,0.9); margin: 0;">
                        Complete your profile today and join the revolution!
                    </p>
                </div>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="https://axi.ideationaxis.com/axi/onboarding" class="cta-button">
                        FINISH YOUR PROFILE NOW →
                    </a>
                    <p style="color: #6b7280; font-size: 13px; margin-top: 15px;">
                        It takes less than 5 minutes to complete!
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
                        </a> • 
                        <a href="https://axi.ideationaxis.com" style="color: #0A2463; text-decoration: none;">
                            AXI Platform
                        </a>
                    </p>
                    <p style="font-size: 11px; color: #9ca3af; margin-top: 20px;">
                        © 2026 Ideation Axis Group. All rights reserved.
                    </p>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    
    try:
        # Normalize email to lowercase
        email = user.email.lower()
        
        result = await graph_client.send_email(
            to_emails=[email],
            subject="🎊 Happy 2026! Complete Your AXI Profile - 3,000+ Builders Waiting!",
            body_html=email_template.format(
                total_onboarded=total_onboarded,
                days_to_launch=DAYS_TO_LAUNCH,
                launch_date=LAUNCH_DATE,
                venue=VENUE,
                ticket_url=TICKET_URL
            ),
            department="general"
        )
        
        logger.info(f"✅ New Year reminder email sent to incomplete user: {email}")
        return {"status": "sent", "email": email, "type": "incomplete"}
    
    except Exception as e:
        logger.error(f"❌ Failed to send email to {user.email}: {e}")
        return {"status": "failed", "email": user.email, "error": str(e)}


async def send_new_year_emails(db: AsyncSession) -> dict:
    """
    Send New Year emails to all AXI users.
    Personalized based on onboarding status.
    """
    logger.info("🎉 Starting New Year 2026 email campaign...")
    
    try:
        # Check if email has already been sent
        # We need to track this in a system setting or user flag
        # For now, we'll assume we haven't sent it yet
        
        # Initialize Microsoft Graph client
        graph_client = get_graph_client()
        
        # Get total onboarded users count for stats
        total_onboarded = 3000
        logger.info(f"📊 Total onboarded users: {total_onboarded}")
        
        # Get all active users who haven't received the email yet
        # Note: You'll need to add a flag to AxiUser model to track this
        # For now, we'll send to all active users
        result = await db.execute(
            select(AxiUser).where(AxiUser.is_active == True)
        )
        users = result.scalars().all()
        
        logger.info(f"📧 Found {len(users)} active users to email")
        
        onboarded_sent = []
        incomplete_sent = []
        failed_emails = []
        
        # Send emails with rate limiting
        for i, user in enumerate(users, 1):
            try:
                # Check if user has already received the email
                # This requires adding a field to AxiUser model
                # For now, we'll send to everyone
                
                if user.onboarding_completed:
                    result = await send_onboarded_user_email(user, graph_client, total_onboarded)
                    if result["status"] == "sent":
                        onboarded_sent.append(result)
                    else:
                        failed_emails.append(result)
                else:
                    result = await send_incomplete_onboarding_email(user, graph_client, total_onboarded)
                    if result["status"] == "sent":
                        incomplete_sent.append(result)
                    else:
                        failed_emails.append(result)
                
                # Mark user as having received the email
                # This requires adding a field to AxiUser model
                # user.new_year_2026_email_sent = True
                
                # Log progress every 50 emails
                if i % 50 == 0:
                    logger.info(f"📧 Progress: {i}/{len(users)} emails processed")
                
                # Rate limiting - wait 2 seconds between emails
                await asyncio.sleep(2)
                
            except Exception as e:
                logger.error(f"❌ Error sending email to {user.email}: {e}")
                failed_emails.append({
                    "status": "failed",
                    "email": user.email,
                    "error": str(e)
                })
        
        # Commit changes (when tracking flag is implemented)
        # await db.commit()
        
        summary = {
            "success": True,
            "timestamp": datetime.now(ACCRA_TIMEZONE).isoformat(),
            "total_users": len(users),
            "total_onboarded": total_onboarded,
            "emails_sent": len(onboarded_sent) + len(incomplete_sent),
            "onboarded_sent": len(onboarded_sent),
            "incomplete_sent": len(incomplete_sent),
            "failed": len(failed_emails),
            "failed_emails": failed_emails[:10] if failed_emails else []  # First 10 failures
        }
        
        logger.info("✅ New Year email campaign completed!")
        logger.info(f"📊 Summary: {len(onboarded_sent)} onboarded, {len(incomplete_sent)} incomplete, {len(failed_emails)} failed")
        
        return summary
        
    except Exception as e:
        logger.error(f"❌ Error in New Year email campaign: {str(e)}")
        await db.rollback()
        raise


async def new_year_email_scheduler():
    """
    Background task that waits until midnight on January 1, 2026 (Accra time)
    and sends New Year emails to all AXI users.
    """
    try:
        logger.info("\n" + "="*80)
        logger.info("🎆 NEW YEAR 2026 EMAIL SCHEDULER STARTING...")
        logger.info("="*80)
        logger.info(f"⏰ Scheduled for: {NEW_YEAR_HOUR:02d}:{NEW_YEAR_MINUTE:02d} on {NEW_YEAR_DAY}/{NEW_YEAR_MONTH}/{NEW_YEAR_YEAR}")
        logger.info(f"🌍 Timezone: {ACCRA_TIMEZONE}")
        
        # Initial delay
        logger.info("⏳ Waiting 10 seconds before starting checks...")
        await asyncio.sleep(10)
        
        scheduled_time_reached = False
        
        while True:
            try:
                now = datetime.now(ACCRA_TIMEZONE)
                
                # Check if we've reached the scheduled New Year time
                if (now.year == NEW_YEAR_YEAR and
                    now.month == NEW_YEAR_MONTH and
                    now.day == NEW_YEAR_DAY and
                    now.hour == NEW_YEAR_HOUR and 
                    now.minute == NEW_YEAR_MINUTE and 
                    not scheduled_time_reached):
                    
                    logger.info(f"\n🎆 NEW YEAR 2026 HAS ARRIVED: {now.strftime('%Y-%m-%d %H:%M:%S')}")
                    logger.info("▶️  Executing New Year email campaign...")
                    
                    # Execute the email campaign
                    async for db in aget_db():
                        try:
                            summary = await send_new_year_emails(db)
                            
                            logger.info("\n" + "="*80)
                            logger.info("📊 NEW YEAR EMAIL CAMPAIGN SUMMARY")
                            logger.info("="*80)
                            logger.info(f"Total users: {summary['total_users']}")
                            logger.info(f"Total onboarded: {summary['total_onboarded']}")
                            logger.info(f"Emails sent: {summary['emails_sent']}")
                            logger.info(f"  - Onboarded users: {summary['onboarded_sent']}")
                            logger.info(f"  - Incomplete users: {summary['incomplete_sent']}")
                            logger.info(f"Failed emails: {summary['failed']}")
                            
                            if summary['failed_emails']:
                                logger.info("\n❌ Failed emails (first 10):")
                                for failed in summary['failed_emails']:
                                    logger.info(f"  - {failed['email']}: {failed.get('error', 'Unknown error')}")
                            
                            logger.info("="*80 + "\n")
                            
                            scheduled_time_reached = True
                            
                        except Exception as e:
                            logger.error(f"❌ Error during email campaign: {e}")
                            import traceback
                            traceback.print_exc()
                        finally:
                            break
                    
                    # After execution, the scheduler can continue running but won't execute again
                    logger.info("✅ New Year email campaign completed. Scheduler will now idle.")
                    logger.info("🔄 Scheduler will continue running but won't send more emails today.")
                    
                # Sleep for 1 minute before next check (more frequent near midnight)
                await asyncio.sleep(60)
                
            except Exception as e:
                logger.error(f"❌ SCHEDULER ERROR: {e}")
                import traceback
                traceback.print_exc()
                await asyncio.sleep(300)  # Wait 5 minutes on error
        
    except Exception as e:
        logger.error(f"❌❌❌ SCHEDULER INITIALIZATION FAILED: {e}")
        import traceback
        traceback.print_exc()


async def start_new_year_scheduler():
    """
    Start the New Year email scheduler.
    This should be called from your main application startup.
    """
    try:
        # Create a background task for the scheduler
        scheduler_task = asyncio.create_task(new_year_email_scheduler())
        
        logger.info("🚀 New Year 2026 Email Scheduler started successfully")
        
        # Return the task so it can be awaited or cancelled if needed
        return scheduler_task
        
    except Exception as e:
        logger.error(f"❌ Failed to start New Year email scheduler: {e}")
        raise


# Optional: Manual trigger for testing
async def manual_trigger_new_year_emails():
    """
    Manually trigger the New Year email campaign for testing purposes.
    This bypasses the scheduler and sends emails immediately.
    """
    try:
        logger.warning("⚠️ MANUALLY TRIGGERING NEW YEAR EMAIL CAMPAIGN (FOR TESTING)")
        
        async for db in aget_db():
            summary = await send_new_year_emails(db)
            
            logger.info("="*80)
            logger.info("🧪 MANUAL TEST SUMMARY")
            logger.info("="*80)
            logger.info(f"Total users: {summary['total_users']}")
            logger.info(f"Total onboarded: {summary['total_onboarded']}")
            logger.info(f"Emails sent: {summary['emails_sent']}")
            logger.info(f"Failed emails: {summary['failed']}")
            logger.info("="*80)
            
            return summary
            
    except Exception as e:
        logger.error(f"❌ Manual trigger failed: {e}")
        raise