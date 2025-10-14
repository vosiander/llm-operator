from injector import Injector
from kubernetes.client import ApiClient
from loguru import logger
import kopf
import kr8s

from src.openwebui_channel.manager import ChannelManagement
from src.openwebui_channel.crd import OpenWebUIChannel

injector: Injector = None
api: ApiClient = None


def register_handlers(inj: Injector):
    global injector, api
    injector = inj
    api = inj.get(ApiClient)
    logger.info("Registering OpenWebUIChannel handlers...")
    OpenWebUIChannel.install(api, exist_ok=True)


@kopf.on.timer("ops.veitosiander.de", "v1", "OpenWebUIChannel", interval=30)
def timer_fn(spec, name, namespace, **kwargs):
    if not spec.get('is_installed', False):
        logger.warning(f"channel not installed for {namespace}/{name}, skipping reconciliation.")
        return

    logger.info("Pinging Open-WebUI service...")
    channel_management = injector.get(ChannelManagement)
    if not channel_management.ping(spec['openwebui_host']):
        logger.error("Failed to ping Open-WebUI service. Will retry in the next interval.")
        return

    logger.info(f"Reconciling OpenWebUIChannel resource: {namespace}/{name} with spec: {spec}")
    cr = list(kr8s.get("OpenWebUIChannel.ops.veitosiander.de", name, namespace=namespace))[0]

    logger.info(f"Fetched CR: {cr} <- {name}")
    
    # Check by ID first, fall back to name
    channel = None
    if spec.get('channel_id'):
        channel = channel_management.get_channel_by_id(spec['openwebui_host'], spec['openwebui_api_key'], spec['channel_id'])
    
    if channel is None:
        channel = channel_management.get_channel_by_name(spec['openwebui_host'], spec['openwebui_api_key'], spec['name'])
    
    if channel is not None:
        logger.info(f"Channel {spec['name']} exists. Nothing to do...")
    else:
        logger.warning(f"Channel {spec['name']} does not exist. Recreating...")
        channel = channel_management.create_channel(spec['openwebui_host'], spec['openwebui_api_key'], spec)
        if channel and channel.get('id'):
            cr.patch({"spec": {"channel_id": channel['id']}})
        logger.info(f"Recreated channel for {namespace}/{name}")


@kopf.on.delete("ops.veitosiander.de", "v1", "OpenWebUIChannel")
def delete_fn(spec, name, namespace, **kwargs):
    channel_management = injector.get(ChannelManagement)

    logger.info(f"Deleting OpenWebUIChannel resource: {namespace}/{name} with spec: {spec}")
    try:
        if spec.get('channel_id'):
            channel_management.delete_channel(spec['openwebui_host'], spec['openwebui_api_key'], spec['channel_id'])
        else:
            channel_management.delete_channel_by_name(spec['openwebui_host'], spec['openwebui_api_key'], spec['name'])
        logger.info(f"OpenWebUIChannel {namespace}/{name} deleted successfully.")
    except Exception as e:
        logger.error(f"Failed to delete channel {spec['name']}: {e}")
        pass


@kopf.on.create("ops.veitosiander.de", "v1", "OpenWebUIChannel")
def create_fn(spec, name, namespace, **kwargs):
    channel_management = injector.get(ChannelManagement)

    logger.info(f"Creating OpenWebUIChannel resource: {namespace}/{name} with spec: {spec}")

    cr = list(kr8s.get("OpenWebUIChannel.ops.veitosiander.de", name, namespace=namespace))[0]
    logger.info(f"Fetched CR: {cr}")

    try:
        channel = channel_management.get_channel_by_name(spec['openwebui_host'], spec['openwebui_api_key'], spec['name'])
        if channel is not None:
            logger.warning(f"Channel with name {spec['name']} already exists. Skipping...")
            # Store the channel ID even if it already exists
            if channel.get('id'):
                cr.patch({"spec": {"channel_id": channel['id'], "is_installed": True}})
            return {"status": "created"}

        logger.info(f"Creating new channel {spec['name']}...")
        channel = channel_management.create_channel(spec['openwebui_host'], spec['openwebui_api_key'], spec)
        logger.info(f"Created channel for {namespace}/{name} with name {channel.get('name', 'no-name')}, updating CRD...")
        
        # Store the channel ID
        patch_data = {"spec": {"is_installed": True}}
        if channel.get('id'):
            patch_data["spec"]["channel_id"] = channel['id']
        cr.patch(patch_data)

        logger.info(f"OpenWebUIChannel {namespace}/{name} created successfully.")
    except Exception as e:
        logger.error(f"Failed to create channel for {namespace}/{name}: {e}")
        raise kopf.TemporaryError(f"Failed to create channel: {e}", delay=30)

    return {"status": "created"}
