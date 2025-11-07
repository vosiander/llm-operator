from injector import Injector
from kubernetes.client import ApiClient
from loguru import logger
import kopf
import kr8s
import base64

from src.openwebui_tool_server.manager import ToolServerManagement
from src.openwebui_tool_server.crd_v1 import OpenWebUIToolServerV1
from src.openwebui_tool_server.crd_v2 import OpenWebUIToolServerV2

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
    logger.info("Registering OpenWebUIToolServer handlers (v1 and v2)...")
    OpenWebUIToolServerV1.install(api, exist_ok=True)
    OpenWebUIToolServerV2.install(api, exist_ok=True)


# V1 Handlers (DEPRECATED - using openwebui_api_key)
@kopf.on.delete("ops.veitosiander.de", "v1", "OpenWebUIToolServer")
def delete_v1(spec, name, namespace, **kwargs):
    tool_server_management = injector.get(ToolServerManagement)
    
    logger.warning(f"Deleting OpenWebUIToolServer v1 resource (DEPRECATED): {namespace}/{name}")
    logger.warning("Please migrate to v2 using existing_secret field")
    
    api_key = spec.get('openwebui_api_key', '').strip()
    
    if not api_key:
        logger.info(f"No API key for {namespace}/{name}, nothing to delete.")
        return
    
    try:
        tool_server_management.delete_tool_server(spec['openwebui_host'], api_key, spec['url'])
        logger.info(f"OpenWebUIToolServer v1 {namespace}/{name} deleted successfully.")
    except Exception as e:
        logger.error(f"Failed to delete tool server {spec['url']}: {e}")
        pass


@kopf.on.create("ops.veitosiander.de", "v1", "OpenWebUIToolServer")
@kopf.on.update("ops.veitosiander.de", "v1", "OpenWebUIToolServer")
def upsert_v1(spec, name, namespace, **kwargs):
    tool_server_management = injector.get(ToolServerManagement)
    
    logger.warning(f"Upserting OpenWebUIToolServer v1 resource (DEPRECATED): {namespace}/{name}")
    logger.warning("Please migrate to v2 using existing_secret field")
    
    api_key = spec.get('openwebui_api_key', '').strip()
    
    if not api_key:
        logger.info(f"No API key for {namespace}/{name}, skipping upsert.")
        return {"status": "waiting_for_api_key"}
    
    try:
        server = tool_server_management.upsert_tool_server(
            spec['openwebui_host'],
            api_key,
            spec
        )
        
        # Update is_installed flag if needed
        if not spec.get('is_installed', False):
            cr = list(kr8s.get("OpenWebUIToolServer.ops.veitosiander.de/v1", name, namespace=namespace))[0]
            cr.patch({"spec": {"is_installed": True}})
        
        logger.info(f"OpenWebUIToolServer v1 {namespace}/{name} upserted successfully.")
        return {"status": "upserted"}
    except Exception as e:
        logger.error(f"Failed to upsert tool server for {namespace}/{name}: {e}")
        raise kopf.TemporaryError(f"Failed to upsert tool server: {e}", delay=30)


# V2 Handlers (NEW - using existing_secret)
@kopf.on.delete("ops.veitosiander.de", "v2", "OpenWebUIToolServer")
def delete_v2(spec, name, namespace, **kwargs):
    tool_server_management = injector.get(ToolServerManagement)
    
    logger.info(f"Deleting OpenWebUIToolServer v2 resource: {namespace}/{name}")
    
    try:
        # Retrieve API key from secret in the same namespace as the CR
        api_key = get_api_key_from_secret(
            spec['existing_secret'],
            namespace
        )
        
        tool_server_management.delete_tool_server(spec['openwebui_host'], api_key, spec['url'])
        logger.info(f"OpenWebUIToolServer v2 {namespace}/{name} deleted successfully.")
    except Exception as e:
        logger.error(f"Failed to delete tool server {spec['url']}: {e}")
        pass


@kopf.on.create("ops.veitosiander.de", "v2", "OpenWebUIToolServer")
@kopf.on.update("ops.veitosiander.de", "v2", "OpenWebUIToolServer")
def upsert_v2(spec, name, namespace, **kwargs):
    tool_server_management = injector.get(ToolServerManagement)
    
    logger.info(f"Upserting OpenWebUIToolServer v2 resource: {namespace}/{name}")
    
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
            cr = list(kr8s.get("OpenWebUIToolServer.ops.veitosiander.de/v2", name, namespace=namespace))[0]
            cr.patch({"spec": {"is_installed": True}})
        
        logger.info(f"OpenWebUIToolServer v2 {namespace}/{name} upserted successfully.")
        return {"status": "upserted"}
    except Exception as e:
        logger.error(f"Failed to upsert tool server for {namespace}/{name}: {e}")
        raise kopf.TemporaryError(f"Failed to upsert tool server: {e}", delay=30)
