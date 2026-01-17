"""Microsoft Teams meeting creation utilities."""

import httpx
from datetime import datetime, timedelta
from typing import Optional
from fastapi import HTTPException

class MicrosoftGraphClient:
    """Client for interacting with Microsoft Graph API."""
    
    BASE_URL = "https://graph.microsoft.com/v1.0"
    
    def __init__(self, tenant_id: str, client_id: str, client_secret: str):
        self.tenant_id = tenant_id
        self.client_id = client_id
        self.client_secret = client_secret
        self._access_token = None
        self._token_expiry = None
    
    async def _get_access_token(self, force_refresh: bool = False) -> str:
        """Get access token for application (not user-delegated)."""
        # Check if we have a valid cached token
        if not force_refresh and self._access_token and self._token_expiry:
            if datetime.utcnow() < self._token_expiry - timedelta(minutes=5):
                return self._access_token
        
        # Get new token
        token_url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
        
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": "https://graph.microsoft.com/.default",
            "grant_type": "client_credentials"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(token_url, data=data)
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to get access token: {response.text}"
                )
            
            token_data = response.json()
            self._access_token = token_data["access_token"]
            expires_in = token_data.get("expires_in", 3600)
            self._token_expiry = datetime.utcnow() + timedelta(seconds=expires_in)
            
            print(f"✅ New access token obtained, expires in {expires_in}s")
            return self._access_token
    
    async def clear_token_cache(self):
        """Force clear the token cache to get fresh permissions."""
        self._access_token = None
        self._token_expiry = None
        print("🔄 Token cache cleared")
    
    async def create_online_meeting(
        self,
        user_email: str,
        subject: str,
        start_time: datetime,
        end_time: datetime,
        participants: list[str] = None,
        retry_with_refresh: bool = True
    ) -> dict:
        """
        Create a Microsoft Teams online meeting via Calendar Event.
        This is more reliable than the /onlineMeetings endpoint.
        
        Args:
            user_email: Email of the user who will be the organizer
            subject: Meeting subject/title
            start_time: Meeting start time (should be timezone-aware)
            end_time: Meeting end time (should be timezone-aware)
            participants: List of participant email addresses
            retry_with_refresh: If True, retry once with a fresh token on 403
        
        Returns:
            dict with meeting details including join_url
        """
        token = await self._get_access_token()
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        # Format datetime for Graph API
        if start_time.tzinfo:
            start_str = start_time.isoformat()
            timezone = str(start_time.tzinfo)
        else:
            start_str = start_time.strftime("%Y-%m-%dT%H:%M:%S")
            timezone = "UTC"
        
        if end_time.tzinfo:
            end_str = end_time.isoformat()
        else:
            end_str = end_time.strftime("%Y-%m-%dT%H:%M:%S")
        
        # Build attendees list
        attendees = []
        if participants:
            attendees = [
                {
                    "emailAddress": {
                        "address": email,
                        "name": email.split('@')[0]
                    },
                    "type": "required"
                }
                for email in participants
            ]
        
        # Create calendar event with Teams meeting
        event_data = {
            "subject": subject,
            "body": {
                "contentType": "HTML",
                "content": f"Join the Teams meeting for: {subject}"
            },
            "start": {
                "dateTime": start_str,
                "timeZone": timezone
            },
            "end": {
                "dateTime": end_str,
                "timeZone": timezone
            },
            "attendees": attendees,
            "isOnlineMeeting": True,
            "onlineMeetingProvider": "teamsForBusiness"
        }
        
        # Create the event using the Calendar API
        url = f"{self.BASE_URL}/users/{user_email}/events"
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                headers=headers,
                json=event_data,
                timeout=30.0
            )
            
            # If 403 and we haven't retried yet, try with a fresh token
            if response.status_code == 403 and retry_with_refresh:
                print("⚠️ Got 403, refreshing token and retrying...")
                await self.clear_token_cache()
                return await self.create_online_meeting(
                    user_email, subject, start_time, end_time, 
                    participants, retry_with_refresh=False
                )
            
            if response.status_code not in [200, 201]:
                error_detail = response.text
                print(f"❌ Failed to create meeting: {response.status_code} - {error_detail}")
                
                # Provide helpful error message
                if response.status_code == 403:
                    error_msg = (
                        "Access denied. Please ensure the app has 'Calendars.ReadWrite' "
                        "(Application permission) and admin consent has been granted. "
                        "Wait 5-10 minutes after granting consent for changes to propagate."
                    )
                else:
                    error_msg = f"Failed to create Teams meeting: {error_detail}"
                
                raise HTTPException(status_code=500, detail=error_msg)
            
            event = response.json()
            
            # Extract the Teams meeting join URL
            online_meeting = event.get("onlineMeeting", {})
            join_url = online_meeting.get("joinUrl")
            
            return {
                "meeting_id": event.get("id"),
                "join_url": join_url,
                "subject": event.get("subject"),
                "start_time": event.get("start", {}).get("dateTime"),
                "end_time": event.get("end", {}).get("dateTime"),
                "online_meeting": online_meeting
            }
    
    async def create_simple_meeting(self, subject: str) -> dict:
        """
        Create a simple online meeting without calendar integration.
        This is useful for ad-hoc meetings like Social Saturday.
        
        Args:
            subject: Meeting subject/title
        
        Returns:
            dict with meeting details including join_url
        """
        token = await self._get_access_token()
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        meeting_data = {
            "subject": subject,
            "allowMeetingChat": "enabled",
            "allowTeamworkReactions": True
        }
        
        url = f"{self.BASE_URL}/communications/onlineMeetings"
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                headers=headers,
                json=meeting_data,
                timeout=30.0
            )
            
            if response.status_code not in [200, 201]:
                print(f"Failed to create simple meeting: {response.status_code} - {response.text}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to create Teams meeting: {response.text}"
                )
            
            meeting = response.json()
            
            return {
                "meeting_id": meeting.get("id"),
                "join_url": meeting.get("joinUrl") or meeting.get("joinWebUrl"),
                "subject": meeting.get("subject")
            }
    
    async def send_email(
        self,
        to_emails: list[str],
        subject: str,
        body_html: str,
        from_email: str = "info@ideationaxis.com",
        body_text: str = None,
        cc_emails: list[str] = None,
        bcc_emails: list[str] = None,
        attachments: list[dict] = None,
        retry_with_refresh: bool = True
    ) -> dict:
        """
        Send an email using Microsoft Graph API.
        
        Args:
            from_email: Email address to send from (must have Send permission)
            to_emails: List of recipient email addresses
            subject: Email subject
            body_html: HTML body content
            body_text: Plain text body (optional, will use HTML if not provided)
            cc_emails: List of CC recipients (optional)
            bcc_emails: List of BCC recipients (optional)
            attachments: List of attachment dicts with 'name', 'contentType', 'contentBytes' (optional)
            retry_with_refresh: If True, retry once with fresh token on 403
        
        Returns:
            dict with status information
        
        Example:
            await graph_client.send_email(
                from_email="sender@company.com",
                to_emails=["user1@company.com", "user2@company.com"],
                subject="Social Sunday Match!",
                body_html="<h1>You've been matched!</h1><p>Check your calendar.</p>",
                cc_emails=["manager@company.com"]
            )
        """
        token = await self._get_access_token()
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        # Build recipient lists
        to_recipients = [
            {"emailAddress": {"address": email}}
            for email in to_emails
        ]
        
        cc_recipients = []
        if cc_emails:
            cc_recipients = [
                {"emailAddress": {"address": email}}
                for email in cc_emails
            ]
        
        bcc_recipients = []
        if bcc_emails:
            bcc_recipients = [
                {"emailAddress": {"address": email}}
                for email in bcc_emails
            ]
        
        # Build message body
        message = {
            "message": {
                "subject": subject,
                "body": {
                    "contentType": "HTML",
                    "content": body_html
                },
                "toRecipients": to_recipients
            },
            "saveToSentItems": "true"
        }
        
        # Add optional fields
        if cc_recipients:
            message["message"]["ccRecipients"] = cc_recipients
        
        if bcc_recipients:
            message["message"]["bccRecipients"] = bcc_recipients
        
        if attachments:
            message["message"]["attachments"] = attachments
        
        # Send email using /sendMail endpoint
        url = f"{self.BASE_URL}/users/{from_email}/sendMail"
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                headers=headers,
                json=message,
                timeout=30.0
            )
            
            # If 403 and we haven't retried yet, try with a fresh token
            if response.status_code == 403 and retry_with_refresh:
                print("⚠️ Email send got 403, refreshing token and retrying...")
                await self.clear_token_cache()
                return await self.send_email(
                    from_email, to_emails, subject, body_html, body_text,
                    cc_emails, bcc_emails, attachments, retry_with_refresh=False
                )
            
            if response.status_code not in [200, 202]:
                error_detail = response.text
                print(f"❌ Failed to send email: {response.status_code} - {error_detail}")
                
                if response.status_code == 403:
                    error_msg = (
                        "Access denied when sending email. Please ensure the app has 'Mail.Send' "
                        "(Application permission) and admin consent has been granted."
                    )
                else:
                    error_msg = f"Failed to send email: {error_detail}"
                
                raise HTTPException(status_code=500, detail=error_msg)
            
            print(f"✅ Email sent successfully from {from_email} to {', '.join(to_emails)}")
            
            return {
                "status": "sent",
                "from": from_email,
                "to": to_emails,
                "subject": subject
            }
    
    async def send_email_with_template(
        self,
        to_emails: list[str],
        subject: str,
        template_html: str,
        from_email: str = "info@ideationaxis.com",
        template_vars: dict = None
    ) -> dict:
        """
        Send an email using a template with variable substitution.
        
        Args:
            from_email: Email address to send from
            to_emails: List of recipient emails
            subject: Email subject (can include template vars like {name})
            template_html: HTML template with placeholders like {name}, {link}
            template_vars: Dictionary of variables to substitute in template
        
        Returns:
            dict with status information
        
        Example:
            await graph_client.send_email_with_template(
                from_email="noreply@company.com",
                to_emails=["user@company.com"],
                subject="Welcome {name}!",
                template_html="<h1>Hi {name}!</h1><p>Your meeting: {meeting_link}</p>",
                template_vars={"name": "John", "meeting_link": "https://teams.microsoft.com/..."}
            )
        """
        if template_vars:
            # Substitute variables in subject and body
            subject = subject.format(**template_vars)
            body_html = template_html.format(**template_vars)
        else:
            body_html = template_html
        
        return await self.send_email(
            from_email=from_email,
            to_emails=to_emails,
            subject=subject,
            body_html=body_html
        )
    
    get_access_token = _get_access_token