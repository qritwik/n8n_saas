import requests
from urllib.parse import urlencode
import config


class GoogleOAuth:
    def __init__(self):
        self.client_id = config.GOOGLE_CLIENT_ID
        self.client_secret = config.GOOGLE_CLIENT_SECRET
        self.redirect_uri = config.REDIRECT_URI

    def get_auth_url(self) -> str:
        """Get Google OAuth authorization URL"""
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": "https://www.googleapis.com/auth/gmail.readonly https://www.googleapis.com/auth/userinfo.email",
            "response_type": "code",
            "access_type": "offline",
            "prompt": "consent",
        }
        return f"https://accounts.google.com/o/oauth2/auth?{urlencode(params)}"

    def exchange_code(self, code: str) -> dict:
        """Exchange authorization code for tokens"""
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": self.redirect_uri,
        }
        response = requests.post("https://oauth2.googleapis.com/token", data=data)
        if response.status_code != 200:
            raise Exception(f"Token exchange failed: {response.text}")
        return response.json()

    def get_user_email(self, access_token: str) -> str:
        """Get user email from access token"""
        response = requests.get(
            "https://www.googleapis.com/oauth2/v1/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if response.status_code != 200:
            raise Exception(f"Failed to get user info: {response.text}")
        return response.json().get("email")
