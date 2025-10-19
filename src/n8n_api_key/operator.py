from injector import Injector
from kubernetes.client import ApiClient
from loguru import logger
import kopf
import kr8s
import os

from src.n8n_api_key.manager import ApiKeyManagement
from src.n8n_api_key.crd import N8nApiKey

injector: Injector = None
api: ApiClient = None

def register_handlers(inj: Injector):
    global injector, api
    injector = inj
    api = inj.get(ApiClient)
    logger.info("Registering N8nApiKey handlers...")
    N8nApiKey.install(api, exist_ok=True)

@kopf.on.create("ops.veitosiander.de", "v1", "N8nApiKey")
def create_fn(spec, name, namespace, **kwargs):
    api_key_management = injector.get(ApiKeyManagement)

    logger.info(f"Creating N8nApiKey resource: {namespace}/{name}")

    try:
        # Step 1: Generate unique key name
        unique_key_name = api_key_management.generate_unique_key_name(spec['api_key_name'])
        logger.info(f"Generated unique key name: {unique_key_name}")

        # Step 2: Login to N8N
        logger.info(f"Logging in to N8N at {spec['n8n_domain']}...")
        auth_cookie = api_key_management.login(
            domain=spec['n8n_domain'],
            email=spec['email'],
            password=spec['password']
        )
        
        if not auth_cookie:
            raise Exception(f"Failed to authenticate with N8N at {spec['n8n_domain']}")

        # Step 3: Create API key
        logger.info(f"Creating API key {unique_key_name} for {spec['n8n_domain']}...")
        api_key_data = api_key_management.create_api_key(
            domain=spec['n8n_domain'],
            auth_cookie=auth_cookie,
            unique_key_name=unique_key_name
        )
        
        if not api_key_data:
            raise Exception(f"Failed to create API key for {spec['n8n_domain']}")

        # Extract data from API key creation response
        api_key = api_key_data["api_key"]
        actual_key_name = api_key_data["unique_key_name"]  # Use actual label from N8N
        user_id = api_key_data["user_id"]
        api_key_id = api_key_data["id"]

        # Step 4: Create Kubernetes secret
        logger.info(f"Creating Kubernetes secret {spec['secret_name']} in namespace {spec['secret_namespace']}...")
        secret_success = api_key_management.create_k8s_secret(
            secret_name=spec['secret_name'],
            namespace=spec['secret_namespace'],
            api_key=api_key,
            api_key_name=actual_key_name,
            api_key_id=api_key_id,
            user_id=user_id
        )
        
        if not secret_success:
            raise Exception(f"Failed to create Kubernetes secret {spec['secret_name']}")

        # Step 5: Update CRD with all N8N API response fields
        logger.info(f"Updating CRD with N8N API key metadata...")
        cr = list(kr8s.get("N8nApiKey.ops.veitosiander.de", name, namespace=namespace))[0]
        cr.patch({
            "spec": {
                "n8n_api_key_name": actual_key_name,
                "user_id": user_id,
                "api_key_id": api_key_id
            }
        })
        
        logger.info(f"CRD updated with: api_key_name={actual_key_name}, user_id={user_id}, api_key_id={api_key_id}")
        
        logger.info(f"N8nApiKey {namespace}/{name} created successfully.")
        return {"status": "created"}
            
    except Exception as e:
        logger.error(f"Failed to create N8nApiKey for {namespace}/{name}: {e}")
        raise kopf.TemporaryError(f"Failed to create N8nApiKey: {e}", delay=30)

@kopf.on.delete("ops.veitosiander.de", "v1", "N8nApiKey")
def delete_fn(spec, name, namespace, **kwargs):
    api_key_management = injector.get(ApiKeyManagement)

    logger.info(f"Deleting N8nApiKey resource: {namespace}/{name}")
    
    try:
        # Delete the API key from N8N if we have the API key ID stored
        if spec.get('api_key_id'):
            logger.info(f"Deleting API key with ID {spec['api_key_id']} from N8N at {spec['n8n_domain']}...")
            
            # Login to N8N
            auth_cookie = api_key_management.login(
                domain=spec['n8n_domain'],
                email=spec['email'],
                password=spec['password']
            )
            
            if auth_cookie:
                api_key_deleted = api_key_management.delete_api_key(
                    domain=spec['n8n_domain'],
                    auth_cookie=auth_cookie,
                    key_id=spec['api_key_id']
                )
                
                if api_key_deleted:
                    logger.info(f"Successfully deleted API key {spec['api_key_id']} from N8N")
                else:
                    logger.warning(f"Failed to delete API key {spec['api_key_id']} from N8N, but continuing")
            else:
                logger.warning(f"Failed to login to N8N for API key deletion, but continuing")
        elif spec.get('n8n_api_key_name'):
            # Backward compatibility - fallback to using key name if no ID (shouldn't happen with new implementation)
            logger.warning(f"No api_key_id found, attempting fallback deletion using key name {spec['n8n_api_key_name']}")
            auth_cookie = api_key_management.login(
                domain=spec['n8n_domain'],
                email=spec['email'],
                password=spec['password']
            )
            
            if auth_cookie:
                api_key_deleted = api_key_management.delete_api_key(
                    domain=spec['n8n_domain'],
                    auth_cookie=auth_cookie,
                    key_id=spec['n8n_api_key_name']
                )
                logger.info(f"Fallback deletion result: {api_key_deleted}")
        else:
            logger.info(f"No API key ID or name stored in CRD, skipping N8N API key deletion")

        # Delete the Kubernetes secret
        success = api_key_management.delete_k8s_secret(
            secret_name=spec['secret_name'],
            namespace=spec['secret_namespace']
        )
        
        if success:
            logger.info(f"Successfully deleted secret {spec['secret_name']} from namespace {spec['secret_namespace']}")
        else:
            logger.warning(f"Failed to delete secret {spec['secret_name']}, but continuing with CRD deletion")
            
        logger.info(f"N8nApiKey {namespace}/{name} deleted successfully.")
                    
    except Exception as e:
        logger.error(f"Error during N8nApiKey deletion for {namespace}/{name}: {e}")

@kopf.on.timer("ops.veitosiander.de", "v1", "N8nApiKey", interval=os.getenv("LLM_OPERATOR_RECONCILE_INTERVAL", 600))
def timer_fn(spec, name, namespace, **kwargs):
    """Reconcile N8nApiKey resources by ensuring the Kubernetes secret exists"""
    logger.info(f"Reconciling N8nApiKey resource: {namespace}/{name}")
    api_key_management = injector.get(ApiKeyManagement)

    if not spec.get('n8n_api_key_name'):
        logger.warning(f"No n8n_api_key_name in spec for {namespace}/{name}, skipping reconciliation")
        return
    
    try:
        # Check if the Kubernetes secret exists using kr8s
        secrets = list(kr8s.get("secrets", spec['secret_name'], namespace=spec['secret_namespace']))
        
        if secrets:
            logger.info(f"Secret {spec['secret_name']} exists in namespace {spec['secret_namespace']}. Nothing to do.")
            return

        logger.warning(f"Secret {spec['secret_name']} not found in namespace {spec['secret_namespace']}. Recreating...")
        
        # Generate new unique key name for recreation
        unique_key_name = api_key_management.generate_unique_key_name(spec['api_key_name'])
        logger.info(f"Generated new unique key name for recreation: {unique_key_name}")
        
        # Login to N8N
        auth_cookie = api_key_management.login(domain=spec['n8n_domain'], email=spec['email'], password=spec['password'])

        if not auth_cookie:
            logger.error(f"Failed to authenticate with N8N for secret recreation")
            return

        # Create new API key
        api_key_data = api_key_management.create_api_key(
            domain=spec['n8n_domain'], 
            auth_cookie=auth_cookie, 
            unique_key_name=unique_key_name
        )
        
        if api_key_data:
            # Extract data from API key creation response
            api_key = api_key_data["api_key"]
            actual_key_name = api_key_data["unique_key_name"]
            user_id = api_key_data["user_id"]
            api_key_id = api_key_data["id"]
            
            # Create secret with all metadata
            api_key_management.create_k8s_secret(
                secret_name=spec['secret_name'], 
                namespace=spec['secret_namespace'], 
                api_key=api_key,
                api_key_name=actual_key_name,
                api_key_id=api_key_id,
                user_id=user_id
            )
            
            # Update CRD with all new fields
            cr = list(kr8s.get("N8nApiKey.ops.veitosiander.de", name, namespace=namespace))[0]
            cr.patch({
                "spec": {
                    "n8n_api_key_name": actual_key_name,
                    "user_id": user_id,
                    "api_key_id": api_key_id
                }
            })
            
            logger.info(f"Recreated secret {spec['secret_name']} and updated CRD for {namespace}/{name}")
            logger.info(f"Updated CRD with: api_key_name={actual_key_name}, user_id={user_id}, api_key_id={api_key_id}")
        else:
            logger.error(f"Failed to recreate API key for {namespace}/{name}")
                
    except Exception as e:
        logger.error(f"Error during N8nApiKey reconciliation for {namespace}/{name}: {e}")
