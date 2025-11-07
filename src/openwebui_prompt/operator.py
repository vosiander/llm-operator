from injector import Injector
from kubernetes.client import ApiClient
from loguru import logger
import kopf
import kr8s
import base64

from src.openwebui_prompt.manager import PromptManagement
from src.openwebui_prompt.crd_v1 import OpenWebUIPromptV1
from src.openwebui_prompt.crd_v2 import OpenWebUIPromptV2

injector: Injector = None
api: ApiClient = None


def get_api_key_from_secret(secret_name: str, secret_namespace: str) -> str:
    """Retrieve OpenWebUI API key from Kubernetes Secret."""
    try:
        secrets = list(kr8s.get("secrets", secret_name, namespace=secret_namespace))
        if not secrets:
            raise ValueError(f"Secret {secret_name} not found in namespace {secret_namespace}")
        
        secret = secrets[0]
        api_key_b64 = secret.data.get('api-key')
        if not api_key_b64:
            raise ValueError(f"Secret {secret_name} does not contain 'api-key' key")
        
        api_key = base64.b64decode(api_key_b64).decode('utf-8')
        return api_key
    except Exception as e:
        logger.error(f"Failed to retrieve API key from secret {secret_namespace}/{secret_name}: {e}")
        raise


def register_handlers(inj: Injector):
    global injector, api
    injector = inj
    api = inj.get(ApiClient)
    logger.info("Registering OpenWebUIPrompt handlers (v1 and v2)...")
    OpenWebUIPromptV1.install(api, exist_ok=True)
    OpenWebUIPromptV2.install(api, exist_ok=True)


# V1 Handlers (DEPRECATED - using openwebui_api_key)
@kopf.on.delete("ops.veitosiander.de", "v1", "OpenWebUIPrompt")
def delete_v1(spec, name, namespace, **kwargs):
    prompt_management = injector.get(PromptManagement)
    
    logger.warning(f"Deleting OpenWebUIPrompt v1 resource (DEPRECATED): {namespace}/{name}")
    logger.warning("Please migrate to v2 using existing_secret field")
    
    api_key = spec.get('openwebui_api_key', '').strip()
    
    if not api_key:
        logger.info(f"No API key for {namespace}/{name}, nothing to delete.")
        return
    
    try:
        prompt_management.delete_prompt(spec['openwebui_host'], api_key, spec['command'])
        logger.info(f"OpenWebUIPrompt v1 {namespace}/{name} deleted successfully.")
    except Exception as e:
        logger.error(f"Failed to delete prompt {spec['command']}: {e}")
        pass


@kopf.on.create("ops.veitosiander.de", "v1", "OpenWebUIPrompt")
@kopf.on.update("ops.veitosiander.de", "v1", "OpenWebUIPrompt")
def upsert_v1(spec, name, namespace, **kwargs):
    prompt_management = injector.get(PromptManagement)
    
    logger.warning(f"Upserting OpenWebUIPrompt v1 resource (DEPRECATED): {namespace}/{name}")
    logger.warning("Please migrate to v2 using existing_secret field")
    
    api_key = spec.get('openwebui_api_key', '').strip()
    
    if not api_key:
        logger.info(f"No API key for {namespace}/{name}, skipping upsert.")
        return {"status": "waiting_for_api_key"}
    
    try:
        prompt = prompt_management.upsert_prompt(
            spec['openwebui_host'],
            api_key,
            spec
        )
        
        # Update is_installed flag if needed
        if not spec.get('is_installed', False):
            cr = list(kr8s.get("OpenWebUIPrompt.ops.veitosiander.de/v1", name, namespace=namespace))[0]
            cr.patch({"spec": {"is_installed": True}})
        
        logger.info(f"OpenWebUIPrompt v1 {namespace}/{name} upserted successfully.")
        return {"status": "upserted"}
    except Exception as e:
        logger.error(f"Failed to upsert prompt for {namespace}/{name}: {e}")
        raise kopf.TemporaryError(f"Failed to upsert prompt: {e}", delay=30)


# V2 Handlers (NEW - using existing_secret)
@kopf.on.delete("ops.veitosiander.de", "v2", "OpenWebUIPrompt")
def delete_v2(spec, name, namespace, **kwargs):
    prompt_management = injector.get(PromptManagement)
    
    logger.info(f"Deleting OpenWebUIPrompt v2 resource: {namespace}/{name}")
    
    try:
        # Retrieve API key from secret in the same namespace as the CR
        api_key = get_api_key_from_secret(
            spec['existing_secret'],
            namespace
        )
        
        prompt_management.delete_prompt(spec['openwebui_host'], api_key, spec['command'])
        logger.info(f"OpenWebUIPrompt v2 {namespace}/{name} deleted successfully.")
    except Exception as e:
        logger.error(f"Failed to delete prompt {spec['command']}: {e}")
        pass


@kopf.on.create("ops.veitosiander.de", "v2", "OpenWebUIPrompt")
@kopf.on.update("ops.veitosiander.de", "v2", "OpenWebUIPrompt")
def upsert_v2(spec, name, namespace, **kwargs):
    prompt_management = injector.get(PromptManagement)
    
    logger.info(f"Upserting OpenWebUIPrompt v2 resource: {namespace}/{name}")
    
    try:
        # Retrieve API key from secret in the same namespace as the CR
        api_key = get_api_key_from_secret(
            spec['existing_secret'],
            namespace
        )
        
        prompt = prompt_management.upsert_prompt(
            spec['openwebui_host'],
            api_key,
            spec
        )
        
        # Update is_installed flag if needed
        if not spec.get('is_installed', False):
            cr = list(kr8s.get("OpenWebUIPrompt.ops.veitosiander.de/v2", name, namespace=namespace))[0]
            cr.patch({"spec": {"is_installed": True}})
        
        logger.info(f"OpenWebUIPrompt v2 {namespace}/{name} upserted successfully.")
        return {"status": "upserted"}
    except Exception as e:
        logger.error(f"Failed to upsert prompt for {namespace}/{name}: {e}")
        raise kopf.TemporaryError(f"Failed to upsert prompt: {e}", delay=30)
