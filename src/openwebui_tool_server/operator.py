from injector import Injector
from kubernetes.client import ApiClient
from loguru import logger
import kopf
import kr8s

from src.openwebui_tool_server.manager import ToolServerManagement
from src.openwebui_tool_server.crd import OpenWebUIToolServer

injector: Injector = None
api: ApiClient = None


def register_handlers(inj: Injector):
    global injector, api
    injector = inj
    api = inj.get(ApiClient)

    logger.info("Registering OpenWebUIToolServer handlers...")
    OpenWebUIToolServer.install(api, exist_ok=True)


@kopf.on.delete("ops.veitosiander.de", "v1", "OpenWebUIToolServer")
def delete_fn(spec, name, namespace, **kwargs):
    api_key = spec.get('openwebui_api_key', '').strip()
    
    if not api_key:
        logger.info(f"No API key for {namespace}/{name}, nothing to delete.")
        return
    
    tool_server_management = injector.get(ToolServerManagement)

    logger.info(f"Deleting OpenWebUIToolServer resource: {namespace}/{name} with spec: {spec}")
    try:
        tool_server_management.delete_tool_server(spec['openwebui_host'], spec['openwebui_api_key'], spec['url'])
        logger.info(f"OpenWebUIToolServer {namespace}/{name} deleted successfully.")
    except Exception as e:
        logger.error(f"Failed to delete tool server {spec['url']}: {e}")
        pass


@kopf.on.create("ops.veitosiander.de", "v1", "OpenWebUIToolServer")
@kopf.on.update("ops.veitosiander.de", "v1", "OpenWebUIToolServer")
def upsert_fn(spec, name, namespace, **kwargs):
    api_key = spec.get('openwebui_api_key', '').strip()
    
    if not api_key:
        logger.info(f"No API key for {namespace}/{name}, skipping upsert.")
        return {"status": "waiting_for_api_key"}
    
    tool_server_management = injector.get(ToolServerManagement)
    
    logger.info(f"Upserting OpenWebUIToolServer resource: {namespace}/{name}")
    
    try:
        server = tool_server_management.upsert_tool_server(
            spec['openwebui_host'],
            spec['openwebui_api_key'],
            spec
        )
        
        # Update is_installed flag if needed
        if not spec.get('is_installed', False):
            cr = list(kr8s.get("OpenWebUIToolServer.ops.veitosiander.de", name, namespace=namespace))[0]
            cr.patch({"spec": {"is_installed": True}})
        
        logger.info(f"OpenWebUIToolServer {namespace}/{name} upserted successfully.")
        return {"status": "upserted"}
    except Exception as e:
        logger.error(f"Failed to upsert tool server for {namespace}/{name}: {e}")
        raise kopf.TemporaryError(f"Failed to upsert tool server: {e}", delay=30)
