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


@kopf.on.timer("ops.veitosiander.de", "v1", "OpenWebUIToolServer", interval=30)
def timer_fn(spec, name, namespace, **kwargs):
    if not spec.get('is_installed', False):
        logger.warning(f"tool server not installed for {namespace}/{name}, skipping reconciliation.")
        return

    logger.info("Pinging Open-WebUI service...")
    tool_server_management = injector.get(ToolServerManagement)
    if not tool_server_management.ping(spec['openwebui_host']):
        logger.error("Failed to ping Open-WebUI service. Will retry in the next interval.")
        return

    logger.info(f"Reconciling OpenWebUIToolServer resource: {namespace}/{name} with spec: {spec}")
    cr = list(kr8s.get("OpenWebUIToolServer.ops.veitosiander.de", name, namespace=namespace))[0]

    logger.info(f"Fetched CR: {cr} <- {name}")
    server = tool_server_management.get_tool_server_by_url(spec['openwebui_host'], spec['openwebui_api_key'], spec['url'])
    if server is not None:
        logger.info(f"Tool server {spec['url']} exists. Nothing to do...")
    else:
        logger.warning(f"Tool server {spec['url']} does not exist. Recreating...")
        tool_server_management.create_tool_server(spec['openwebui_host'], spec['openwebui_api_key'], spec)
        logger.info(f"Recreated tool server for {namespace}/{name}")


@kopf.on.delete("ops.veitosiander.de", "v1", "OpenWebUIToolServer")
def delete_fn(spec, name, namespace, **kwargs):
    tool_server_management = injector.get(ToolServerManagement)

    logger.info(f"Deleting OpenWebUIToolServer resource: {namespace}/{name} with spec: {spec}")
    try:
        tool_server_management.delete_tool_server(spec['openwebui_host'], spec['openwebui_api_key'], spec['url'])
        logger.info(f"OpenWebUIToolServer {namespace}/{name} deleted successfully.")
    except Exception as e:
        logger.error(f"Failed to delete tool server {spec['url']}: {e}")
        pass


@kopf.on.create("ops.veitosiander.de", "v1", "OpenWebUIToolServer")
def create_fn(spec, name, namespace, **kwargs):
    tool_server_management = injector.get(ToolServerManagement)

    logger.info(f"Creating OpenWebUIToolServer resource: {namespace}/{name} with spec: {spec}")

    cr = list(kr8s.get("OpenWebUIToolServer.ops.veitosiander.de", name, namespace=namespace))[0]
    logger.info(f"Fetched CR: {cr}")

    try:
        server = tool_server_management.get_tool_server_by_url(spec['openwebui_host'], spec['openwebui_api_key'], spec['url'])
        if server is not None:
            logger.warning(f"Tool server with URL {spec['url']} already exists. Skipping...")
            return {"status": "created"}

        logger.info(f"Creating new tool server {spec['url']}...")
        server = tool_server_management.create_tool_server(spec['openwebui_host'], spec['openwebui_api_key'], spec)
        logger.info(f"Created tool server for {namespace}/{name} with URL {server.get('url', 'no-url')}, updating CRD...")
        cr.patch({"spec": {"is_installed": True}})

        logger.info(f"OpenWebUIToolServer {namespace}/{name} created successfully.")
    except Exception as e:
        logger.error(f"Failed to create tool server for {namespace}/{name}: {e}")
        raise kopf.TemporaryError(f"Failed to create tool server: {e}", delay=30)

    return {"status": "created"}
