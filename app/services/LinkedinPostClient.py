import httpx
from typing import Optional, Dict
from datetime import datetime, timedelta

class LinkedInClient:
    """Client for LinkedIn API integration."""
    
    BASE_URL = "https://api.linkedin.com/v2"
    
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0"
        }
    
    async def create_share(
        self,
        author_urn: str,  # User's LinkedIn URN (e.g., urn:li:person:ABC123)
        text: str,
        visibility: str = "PUBLIC"
    ) -> Dict:
        """
        Create a LinkedIn post/share.
        
        Args:
            author_urn: LinkedIn URN of the author
            text: Post content
            visibility: PUBLIC or CONNECTIONS
        
        Returns:
            Dict with post details including post_id and share_url
        """
        
        share_data = {
            "author": author_urn,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {
                        "text": text
                    },
                    "shareMediaCategory": "NONE"
                }
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": visibility
            }
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.BASE_URL}/ugcPosts",
                headers=self.headers,
                json=share_data,
                timeout=30.0
            )
            
            if response.status_code not in [200, 201]:
                raise Exception(f"LinkedIn API error: {response.status_code} - {response.text}")
            
            result = response.json()
            
            # Extract post ID from the response header or body
            post_id = result.get("id")
            
            # Construct share URL
            share_url = f"https://www.linkedin.com/feed/update/{post_id}/"
            
            return {
                "post_id": post_id,
                "share_url": share_url,
                "created_at": datetime.utcnow().isoformat()
            }
    
    async def get_user_profile(self) -> Dict:
        """Get the authenticated user's LinkedIn profile."""
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/me",
                headers=self.headers,
                timeout=30.0
            )
            
            if response.status_code != 200:
                raise Exception(f"LinkedIn API error: {response.status_code}")
            
            return response.json()