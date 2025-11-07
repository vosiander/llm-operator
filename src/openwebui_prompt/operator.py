from injector import Injector
from kubernetes.client import ApiClient
from loguru import logger
import kopf
import kr8s
import base64

from src.openwebui_prompt.manager import PromptManagement
from src.openwebui_prompt.crd import OpenWebUIPrompt

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
    logger.info("Registering OpenWebUIPrompt handlers...")
    OpenWebUIPrompt.install(api, exist_ok=True)


@kopf.on.delete("ops.veitosiander.de", "v1", "OpenWebUIPrompt")
def delete_fn(spec, name, namespace, **kwargs):
    prompt_management = injector.get(PromptManagement)
    
    logger.info(f"Deleting OpenWebUIPrompt resource: {namespace}/{name}")
    
    try:
        # Retrieve API key from secret in the same namespace as the CR
        api_key = get_api_key_from_secret(
            spec['existing_secret'],
            namespace
        )
        
        prompt_management.delete_prompt(spec['openwebui_host'], api_key, spec['command'])
        logger.info(f"OpenWebUIPrompt {namespace}/{name} deleted successfully.")
    except Exception as e:
        logger.error(f"Failed to delete prompt {spec['command']}: {e}")
        pass


@kopf.on.create("ops.veitosiander.de", "v1", "OpenWebUIPrompt")
@kopf.on.update("ops.veitosiander.de", "v1", "OpenWebUIPrompt")
def upsert_fn(spec, name, namespace, **kwargs):
    prompt_management = injector.get(PromptManagement)
    
    logger.info(f"Upserting OpenWebUIPrompt resource: {namespace}/{name}")
    
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
            cr = list(kr8s.get("OpenWebUIPrompt.ops.veitosiander.de/v1", name, namespace=namespace))[0]
            cr.patch({"spec": {"is_installed": True}})
        
        logger.info(f"OpenWebUIPrompt {namespace}/{name} upserted successfully.")
        return {"status": "upserted"}
    except Exception as e:
        logger.error(f"Failed to upsert prompt for {namespace}/{name}: {e}")
        raise kopf.TemporaryError(f"Failed to upsert prompt: {e}", delay=30)
