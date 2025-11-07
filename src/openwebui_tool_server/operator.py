from injector import Injector
from kubernetes.client import ApiClient
from loguru import logger
import kopf
import kr8s
import base64

from src.openwebui_tool_server.manager import ToolServerManagement
from src.openwebui_tool_server.crd import OpenWebUIToolServer

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
    logger.info("Registering OpenWebUIToolServer handlers...")
    OpenWebUIToolServer.install(api, exist_ok=True)


@kopf.on.delete("ops.veitosiander.de", "v1", "OpenWebUIToolServer")
def delete_fn(spec, name, namespace, **kwargs):
    tool_server_management = injector.get(ToolServerManagement)
    
    logger.info(f"Deleting OpenWebUIToolServer resource: {namespace}/{name}")
    
    try:
        # Retrieve API key from secret in the same namespace as the CR
        api_key = get_api_key_from_secret(
            spec['existing_secret'],
            namespace
        )
        
        tool_server_management.delete_tool_server(spec['openwebui_host'], api_key, spec['url'])
        logger.info(f"OpenWebUIToolServer {namespace}/{name} deleted successfully.")
    except Exception as e:
        logger.error(f"Failed to delete tool server {spec['url']}: {e}")
        pass


@kopf.on.create("ops.veitosiander.de", "v1", "OpenWebUIToolServer")
@kopf.on.update("ops.veitosiander.de", "v1", "OpenWebUIToolServer")
def upsert_fn(spec, name, namespace, **kwargs):
    tool_server_management = injector.get(ToolServerManagement)
    
    logger.info(f"Upserting OpenWebUIToolServer resource: {namespace}/{name}")
    
    try:
        # Retrieve API key from secret in the same namespace as the CR
        api_key = get_api_key_from_secret(
            spec['existing_secret'],
            namespace
        )
        
        server = tool_server_management.upsert_tool_server(
            spec['openwebui_host'],
            api_key,
            spec
        )
        
        # Update is_installed flag if needed
        if not spec.get('is_installed', False):
            cr = list(kr8s.get("OpenWebUIToolServer.ops.veitosiander.de/v1", name, namespace=namespace))[0]
            cr.patch({"spec": {"is_installed": True}})
        
        logger.info(f"OpenWebUIToolServer {namespace}/{name} upserted successfully.")
        return {"status": "upserted"}
    except Exception as e:
        logger.error(f"Failed to upsert tool server for {namespace}/{name}: {e}")
        raise kopf.TemporaryError(f"Failed to upsert tool server: {e}", delay=30)
