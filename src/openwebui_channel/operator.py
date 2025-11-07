from injector import Injector
from kubernetes.client import ApiClient
from loguru import logger
import kopf
import kr8s
import base64

from src.openwebui_channel.manager import ChannelManagement
from src.openwebui_channel.crd_v1 import OpenWebUIChannelV1
from src.openwebui_channel.crd_v2 import OpenWebUIChannelV2

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
    logger.info("Registering OpenWebUIChannel handlers (v1 and v2)...")
    OpenWebUIChannelV1.install(api, exist_ok=True)
    OpenWebUIChannelV2.install(api, exist_ok=True)


# V1 Handlers (DEPRECATED - using openwebui_api_key)
@kopf.on.delete("ops.veitosiander.de", "v1", "OpenWebUIChannel")
def delete_v1(spec, name, namespace, **kwargs):
    channel_management = injector.get(ChannelManagement)
    
    logger.warning(f"Deleting OpenWebUIChannel v1 resource (DEPRECATED): {namespace}/{name}")
    logger.warning("Please migrate to v2 using existing_secret field")
    
    api_key = spec.get('openwebui_api_key', '').strip()
    
    if not api_key:
        logger.info(f"No API key for {namespace}/{name}, nothing to delete.")
        return
    
    try:
        if spec.get('channel_id'):
            channel_management.delete_channel(spec['openwebui_host'], api_key, spec['channel_id'])
        else:
            channel_management.delete_channel_by_name(spec['openwebui_host'], api_key, spec['name'])
        logger.info(f"OpenWebUIChannel v1 {namespace}/{name} deleted successfully.")
    except Exception as e:
        logger.error(f"Failed to delete channel {spec['name']}: {e}")
        pass


@kopf.on.create("ops.veitosiander.de", "v1", "OpenWebUIChannel")
@kopf.on.update("ops.veitosiander.de", "v1", "OpenWebUIChannel")
def upsert_v1(spec, name, namespace, **kwargs):
    channel_management = injector.get(ChannelManagement)
    
    logger.warning(f"Upserting OpenWebUIChannel v1 resource (DEPRECATED): {namespace}/{name}")
    logger.warning("Please migrate to v2 using existing_secret field")
    
    api_key = spec.get('openwebui_api_key', '').strip()
    
    if not api_key:
        logger.info(f"No API key for {namespace}/{name}, skipping upsert.")
        return {"status": "waiting_for_api_key"}
    
    try:
        channel = channel_management.upsert_channel(
            spec['openwebui_host'],
            api_key,
            spec,
            spec.get('channel_id')
        )
        
        # Update is_installed and channel_id if needed
        patch_data = {}
        if not spec.get('is_installed', False):
            patch_data["is_installed"] = True
        if channel and channel.get('id') and channel.get('id') != spec.get('channel_id'):
            patch_data["channel_id"] = channel['id']
        
        if patch_data:
            cr = list(kr8s.get("OpenWebUIChannel.ops.veitosiander.de/v1", name, namespace=namespace))[0]
            cr.patch({"spec": patch_data})
            logger.info(f"Updated CRD for {namespace}/{name}: {patch_data}")
        
        logger.info(f"OpenWebUIChannel v1 {namespace}/{name} upserted successfully.")
        return {"status": "upserted"}
    except Exception as e:
        logger.error(f"Failed to upsert channel for {namespace}/{name}: {e}")
        raise kopf.TemporaryError(f"Failed to upsert channel: {e}", delay=30)


# V2 Handlers (NEW - using existing_secret)
@kopf.on.delete("ops.veitosiander.de", "v2", "OpenWebUIChannel")
def delete_v2(spec, name, namespace, **kwargs):
    channel_management = injector.get(ChannelManagement)
    
    logger.info(f"Deleting OpenWebUIChannel v2 resource: {namespace}/{name}")
    
    try:
        # Retrieve API key from secret in the same namespace as the CR
        api_key = get_api_key_from_secret(
            spec['existing_secret'],
            namespace
        )
        
        if spec.get('channel_id'):
            channel_management.delete_channel(spec['openwebui_host'], api_key, spec['channel_id'])
        else:
            channel_management.delete_channel_by_name(spec['openwebui_host'], api_key, spec['name'])
        logger.info(f"OpenWebUIChannel v2 {namespace}/{name} deleted successfully.")
    except Exception as e:
        logger.error(f"Failed to delete channel {spec['name']}: {e}")
        pass


@kopf.on.create("ops.veitosiander.de", "v2", "OpenWebUIChannel")
@kopf.on.update("ops.veitosiander.de", "v2", "OpenWebUIChannel")
def upsert_v2(spec, name, namespace, **kwargs):
    channel_management = injector.get(ChannelManagement)
    
    logger.info(f"Upserting OpenWebUIChannel v2 resource: {namespace}/{name}")
    
    try:
        # Retrieve API key from secret in the same namespace as the CR
        api_key = get_api_key_from_secret(
            spec['existing_secret'],
            namespace
        )
        
        channel = channel_management.upsert_channel(
            spec['openwebui_host'],
            api_key,
            spec,
            spec.get('channel_id')
        )
        
        # Update is_installed and channel_id if needed
        patch_data = {}
        if not spec.get('is_installed', False):
            patch_data["is_installed"] = True
        if channel and channel.get('id') and channel.get('id') != spec.get('channel_id'):
            patch_data["channel_id"] = channel['id']
        
        if patch_data:
            cr = list(kr8s.get("OpenWebUIChannel.ops.veitosiander.de/v2", name, namespace=namespace))[0]
            cr.patch({"spec": patch_data})
            logger.info(f"Updated CRD for {namespace}/{name}: {patch_data}")
        
        logger.info(f"OpenWebUIChannel v2 {namespace}/{name} upserted successfully.")
        return {"status": "upserted"}
    except Exception as e:
        logger.error(f"Failed to upsert channel for {namespace}/{name}: {e}")
        raise kopf.TemporaryError(f"Failed to upsert channel: {e}", delay=30)
