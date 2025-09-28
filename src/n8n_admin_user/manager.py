from injector import singleton
from loguru import logger
import requests
import os

@singleton
class AdminUserManagement:
    def __init__(self):
        self.request_timeout = int(os.getenv("N8N_REQUEST_TIMEOUT", "30"))
        pass

    def create_admin_user(self, domain: str, email: str, first_name: str, last_name: str, password: str) -> bool:
        """Create admin user via N8N owner setup API"""
        try:
            url = f"{domain}/rest/owner/setup"
            payload = {
                "email": email,
                "firstName": first_name,
                "lastName": last_name,
                "password": password
            }
            
            response = requests.post(url, json=payload, timeout=self.request_timeout)
            if response.status_code != 200:
                logger.error(f"Failed to create admin user for {domain}: {response.status_code} - {response.text}")
                return False
                
        except requests.RequestException as e:
            logger.error(f"Error creating admin user for {domain}: {e}")
            return False

        return True

    def login(self, domain: str, email: str, password: str) -> str:
        """Login to N8N and return auth cookie"""
        try:
            url = f"{domain}/rest/login"
            payload = {
                "emailOrLdapLoginId": email,
                "password": password
            }

            response = requests.post(url, json=payload, timeout=self.request_timeout)

            if response.status_code != 200:
                logger.error(f"No auth cookie received from {domain}")
                return None

            auth_cookie = response.cookies.get('n8n-auth')
            if auth_cookie:
                logger.info(f"Successfully logged in to {domain}")
                return auth_cookie

        except requests.RequestException as e:
            logger.error(f"Error logging in to {domain}: {e}")
            return None

        return None
