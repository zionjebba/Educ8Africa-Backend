"""Microsoft Graph Client for Public/External Communications."""

import httpx
from datetime import datetime, timedelta
from fastapi import HTTPException


class MicrosoftGraphClientPublic:
    """
    Client for sending emails to external/public recipients.
    
    This client uses a single authorized sender mailbox and supports
    reply-to headers for routing responses to appropriate departments.
    """
    
    BASE_URL = "https://graph.microsoft.com/v1.0"
    
    # The authorized sender email that exists in your M365 tenant
    DEFAULT_SENDER = "axi@ideationaxis.com"
    
    # Department reply-to addresses
    REPLY_TO_ADDRESSES = {
        "partnerships": "partnerships@ideationaxis.com",
        "events": "events@ideationaxis.com",
        "sponsorship": "sponsorship@ideationaxis.com",
        "volunteer": "volunteer@ideationaxis.com",
        "general": "info@ideationaxis.com",
        "noreply": "noreply@ideationaxis.com",
    }
    
    def __init__(
        self,
        tenant_id: str,
        client_id: str,
        client_secret: str,
        default_sender: str = None
    ):
        self.tenant_id = tenant_id
        self.client_id = client_id
        self.client_secret = client_secret
        self.default_sender = default_sender or self.DEFAULT_SENDER
        self._access_token = None
        self._token_expiry = None
    
    async def _get_access_token(self, force_refresh: bool = False) -> str:
        """Get access token for application (not user-delegated)."""
        if not force_refresh and self._access_token and self._token_expiry:
            if datetime.utcnow() < self._token_expiry - timedelta(minutes=5):
                return self._access_token
        
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
            
            print(f"✅ [Public Client] New access token obtained, expires in {expires_in}s")
            return self._access_token
    
    async def clear_token_cache(self):
        """Force clear the token cache to get fresh permissions."""
        self._access_token = None
        self._token_expiry = None
        print("🔄 [Public Client] Token cache cleared")
    
    def get_reply_to(self, department: str) -> str:
        """Get the reply-to address for a department."""
        return self.REPLY_TO_ADDRESSES.get(department, self.REPLY_TO_ADDRESSES["general"])
    
    async def send_email(
        self,
        to_emails: list[str],
        subject: str,
        body_html: str,
        reply_to: str = None,
        department: str = None,
        cc_emails: list[str] = None,
        bcc_emails: list[str] = None,
        attachments: list[dict] = None,
        retry_with_refresh: bool = True
    ) -> dict:
        """
        Send an email to external recipients.
        
        Args:
            to_emails: List of recipient email addresses (can be ANY email)
            subject: Email subject
            body_html: HTML body content
            reply_to: Custom reply-to address (overrides department)
            department: Department name for reply-to (partnerships, events, etc.)
            cc_emails: List of CC recipients (optional)
            bcc_emails: List of BCC recipients (optional)
            attachments: List of attachment dicts (optional)
            retry_with_refresh: If True, retry once with fresh token on 403
        
        Returns:
            dict with status information
        
        Example:
            await client.send_email(
                to_emails=["applicant@gmail.com"],
                subject="Application Received",
                body_html="<h1>Thank you!</h1>",
                department="partnerships"
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
        
        # Build message
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
        
        # Determine reply-to address
        final_reply_to = reply_to or (self.get_reply_to(department) if department else None)
        if final_reply_to:
            message["message"]["replyTo"] = [
                {"emailAddress": {"address": final_reply_to}}
            ]
        
        # Add optional fields
        if cc_recipients:
            message["message"]["ccRecipients"] = cc_recipients
        
        if bcc_recipients:
            message["message"]["bccRecipients"] = bcc_recipients
        
        if attachments:
            message["message"]["attachments"] = attachments
        
        # Send email using the default authorized sender
        url = f"{self.BASE_URL}/users/{self.default_sender}/sendMail"
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                headers=headers,
                json=message,
                timeout=30.0
            )
            
            if response.status_code == 403 and retry_with_refresh:
                print("⚠️ [Public Client] Email send got 403, refreshing token and retrying...")
                await self.clear_token_cache()
                return await self.send_email(
                    to_emails, subject, body_html, reply_to, department,
                    cc_emails, bcc_emails, attachments, retry_with_refresh=False
                )
            
            if response.status_code not in [200, 202]:
                error_detail = response.text
                print(f"❌ [Public Client] Failed to send email: {response.status_code} - {error_detail}")
                
                if response.status_code == 403:
                    error_msg = (
                        "Access denied when sending email. Please ensure: "
                        "1) The app has 'Mail.Send' application permission with admin consent. "
                        f"2) The sender mailbox '{self.default_sender}' exists in your M365 tenant."
                    )
                else:
                    error_msg = f"Failed to send email: {error_detail}"
                
                raise HTTPException(status_code=500, detail=error_msg)
            
            print(f"✅ [Public Client] Email sent to {', '.join(to_emails)} (reply-to: {final_reply_to or 'none'})")
            
            return {
                "status": "sent",
                "from": self.default_sender,
                "to": to_emails,
                "reply_to": final_reply_to,
                "subject": subject
            }
    
    async def send_email_with_template(
        self,
        to_emails: list[str],
        subject: str,
        template_html: str,
        template_vars: dict = None,
        reply_to: str = None,
        department: str = None,
        cc_emails: list[str] = None,
        bcc_emails: list[str] = None
    ) -> dict:
        """
        Send an email using a template with variable substitution.
        
        Args:
            to_emails: List of recipient emails
            subject: Email subject (can include template vars like {name})
            template_html: HTML template with placeholders like {name}, {link}
            template_vars: Dictionary of variables to substitute in template
            reply_to: Custom reply-to address
            department: Department name for reply-to routing
            cc_emails: List of CC recipients
            bcc_emails: List of BCC recipients
        
        Returns:
            dict with status information
        
        Example:
            await client.send_email_with_template(
                to_emails=["applicant@gmail.com"],
                subject="Welcome {name}!",
                template_html="<h1>Hi {name}!</h1><p>Your ID: {application_id}</p>",
                template_vars={"name": "John", "application_id": "ABC123"},
                department="partnerships"
            )
        """
        if template_vars:
            subject = subject.format(**template_vars)
            body_html = template_html.format(**template_vars)
        else:
            body_html = template_html
        
        return await self.send_email(
            to_emails=to_emails,
            subject=subject,
            body_html=body_html,
            reply_to=reply_to,
            department=department,
            cc_emails=cc_emails,
            bcc_emails=bcc_emails
        )
    
    async def send_user_confirmation(
        self,
        to_email: str,
        subject: str,
        template_html: str,
        template_vars: dict,
        department: str
    ) -> dict:
        """
        Convenience method for sending user confirmation emails.
        Reply-to is set to the appropriate department.
        """
        return await self.send_email_with_template(
            to_emails=[to_email],
            subject=subject,
            template_html=template_html,
            template_vars=template_vars,
            department=department
        )
    
    async def send_admin_notification(
        self,
        admin_emails: list[str],
        subject: str,
        template_html: str,
        template_vars: dict,
        reply_to_applicant: str
    ) -> dict:
        """
        Convenience method for sending admin notification emails.
        Reply-to is set to the applicant's email for easy response.
        """
        return await self.send_email_with_template(
            to_emails=admin_emails,
            subject=subject,
            template_html=template_html,
            template_vars=template_vars,
            reply_to=reply_to_applicant
        )