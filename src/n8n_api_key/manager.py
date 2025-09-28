from injector import singleton
from kr8s.objects import Secret
from loguru import logger
import requests
import os
import secrets
import string
import kr8s
import base64

@singleton
class ApiKeyManagement:
    def __init__(self):
        self.request_timeout = int(os.getenv("N8N_REQUEST_TIMEOUT", "30"))
        # Full scopes from the original shell script for non-enterprise customers
        self.n8n_scopes = [
            "user:read", "user:list", "user:create", "user:changeRole", "user:delete", "user:enforceMfa",
            "sourceControl:pull", "securityAudit:generate", "project:create", "project:update", 
            "project:delete", "project:list", "variable:create", "variable:delete", "variable:list", 
            "variable:update", "tag:create", "tag:read", "tag:update", "tag:delete", "tag:list", 
            "workflowTags:update", "workflowTags:list", "workflow:create", "workflow:read", 
            "workflow:update", "workflow:delete", "workflow:list", "workflow:move", 
            "workflow:activate", "workflow:deactivate", "execution:delete", "execution:read", 
            "execution:list", "credential:create", "credential:move", "credential:delete"
        ]
        pass

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

    def generate_unique_key_name(self, base_name: str) -> str:
        """Generate a unique API key name with random suffix"""
        random_suffix = ''.join(secrets.choice(string.ascii_lowercase + string.digits) for _ in range(8))
        return f"{base_name}-{random_suffix}"

    def create_api_key(self, domain: str, auth_cookie: str, unique_key_name: str) -> dict:
        """Create API key via N8N API and return dict with api_key, unique_key_name, user_id, and id"""
        try:
            logger.info(f"Creating API key with name: {unique_key_name}")
            logger.info(f"Using {len(self.n8n_scopes)} scopes for full N8N access")
            
            url = f"{domain}/rest/api-keys"
            payload = {
                "label": unique_key_name,
                "expiresAt": None,
                "scopes": self.n8n_scopes
            }
            
            headers = {
                "Content-Type": "application/json",
                "Cookie": f"n8n-auth={auth_cookie}"
            }
            
            response = requests.post(url, json=payload, headers=headers, timeout=self.request_timeout)
            logger.debug(f"Create API key response: {response.status_code} - {response.text}")

            result = response.json()
            data = result.get('data', {})
            
            # Extract all required fields from N8N API response
            api_key = data.get('rawApiKey')
            api_key_id = data.get('id')
            user_id = data.get('userId')
            label = data.get('label')
            
            if api_key and api_key_id and user_id:
                logger.info(f"Successfully created API key for {domain}")
                logger.info(f"API Key ID: {api_key_id}, User ID: {user_id}, Label: {label}")
                
                return {
                    "api_key": api_key,
                    "unique_key_name": label,
                    "user_id": user_id,
                    "id": api_key_id
                }

            logger.error(f"Missing required fields in response from {domain}: {result}")
            return None

        except requests.RequestException as e:
            logger.error(f"Error creating API key for {domain}: {e}")
            return None

    def delete_api_key(self, domain: str, auth_cookie: str, key_id: str) -> bool:
        """Delete API key via N8N API"""
        try:
            url = f"{domain}/rest/api-keys/{key_id}"
            headers = {
                "Cookie": f"n8n-auth={auth_cookie}"
            }
            
            response = requests.delete(url, headers=headers, timeout=self.request_timeout)

            logger.debug(f"Delete API key response: {response.status_code} - {response.text}")
            
            if response.status_code == 200:
                logger.info(f"Successfully deleted API key {key_id} from {domain}")
                return True
            else:
                logger.error(f"Failed to delete API key {key_id} from {domain}: {response.status_code} - {response.text}")
                return False
                
        except requests.RequestException as e:
            logger.error(f"Error deleting API key {key_id} from {domain}: {e}")
            return False

    def create_k8s_secret(self, secret_name: str, namespace: str, api_key: str, api_key_name: str, api_key_id: str, user_id: str) -> bool:
        """Create Kubernetes secret with all N8N API key metadata"""
        try:
            # Delete existing secret if it exists
            try:
                existing_secrets = list(kr8s.get("secrets", secret_name, namespace=namespace))
                if existing_secrets:
                    existing_secrets[0].delete()
                    logger.info(f"Deleted existing secret {secret_name} in namespace {namespace}")
            except Exception as e:
                logger.debug(f"No existing secret to delete: {e}")
            
            # Create new secret with base64 encoded data
            Secret({
                "apiVersion": "v1",
                "kind": "Secret",
                "metadata": {
                    "name": secret_name,
                    "namespace": namespace
                },
                "data": {
                    "api-key": base64.b64encode(api_key.encode()).decode(),
                    "api-key-name": base64.b64encode(api_key_name.encode()).decode(),
                    "api-key-id": base64.b64encode(api_key_id.encode()).decode(),
                    "user-id": base64.b64encode(user_id.encode()).decode()
                }
            }).create()
            logger.info(f"Successfully created secret {secret_name} in namespace {namespace}")
            logger.info(f"Secret contains: api-key, api-key-name ({api_key_name}), api-key-id ({api_key_id}), user-id ({user_id})")
            return True
            
        except Exception as e:
            logger.error(f"Error creating Kubernetes secret {secret_name}: {e}")
            return False

    def delete_k8s_secret(self, secret_name: str, namespace: str) -> bool:
        """Delete Kubernetes secret"""
        try:
            secrets = list(kr8s.get("secrets", secret_name, namespace=namespace))
            if secrets:
                secrets[0].delete()
                logger.info(f"Successfully deleted secret {secret_name} from namespace {namespace}")
            else:
                logger.info(f"Secret {secret_name} not found in namespace {namespace}, nothing to delete")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting Kubernetes secret {secret_name}: {e}")
            return False
