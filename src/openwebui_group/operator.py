from injector import Injector
from kubernetes.client import ApiClient
from loguru import logger
import kopf
import kr8s
import base64

from src.openwebui_group.manager import GroupManagement
from src.openwebui_group.crd_v1 import OpenWebUIGroupV1
from src.openwebui_group.crd_v2 import OpenWebUIGroupV2

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
    logger.info("Registering OpenWebUIGroup handlers (v1 and v2)...")
    OpenWebUIGroupV1.install(api, exist_ok=True)
    OpenWebUIGroupV2.install(api, exist_ok=True)


# V1 Handlers (DEPRECATED - using openwebui_api_key)
@kopf.on.delete("ops.veitosiander.de", "v1", "OpenWebUIGroup")
def delete_v1(spec, name, namespace, **kwargs):
    group_management = injector.get(GroupManagement)
    
    logger.warning(f"Deleting OpenWebUIGroup v1 resource (DEPRECATED): {namespace}/{name}")
    logger.warning("Please migrate to v2 using existing_secret field")
    
    api_key = spec.get('openwebui_api_key', '').strip()
    
    if not api_key:
        logger.info(f"No API key for {namespace}/{name}, nothing to delete.")
        return
    
    try:
        if spec.get('group_id'):
            group_management.delete_group(spec['openwebui_host'], api_key, spec['group_id'])
        else:
            group_management.delete_group_by_name(spec['openwebui_host'], api_key, spec['name'])
        logger.info(f"OpenWebUIGroup v1 {namespace}/{name} deleted successfully.")
    except Exception as e:
        logger.error(f"Failed to delete group {spec['name']}: {e}")
        pass


@kopf.on.create("ops.veitosiander.de", "v1", "OpenWebUIGroup")
@kopf.on.update("ops.veitosiander.de", "v1", "OpenWebUIGroup")
def upsert_v1(spec, name, namespace, **kwargs):
    group_management = injector.get(GroupManagement)
    
    logger.warning(f"Upserting OpenWebUIGroup v1 resource (DEPRECATED): {namespace}/{name}")
    logger.warning("Please migrate to v2 using existing_secret field")
    
    api_key = spec.get('openwebui_api_key', '').strip()
    
    if not api_key:
        logger.info(f"No API key for {namespace}/{name}, skipping upsert.")
        return {"status": "waiting_for_api_key"}
    
    try:
        group = group_management.upsert_group(
            spec['openwebui_host'],
            api_key,
            spec,
            spec.get('group_id')
        )
        
        # Update is_installed and group_id if needed
        patch_data = {}
        if not spec.get('is_installed', False):
            patch_data["is_installed"] = True
        if group and group.get('id') and group.get('id') != spec.get('group_id'):
            patch_data["group_id"] = group['id']
        
        if patch_data:
            cr = list(kr8s.get("OpenWebUIGroup.ops.veitosiander.de/v1", name, namespace=namespace))[0]
            cr.patch({"spec": patch_data})
            logger.info(f"Updated CRD for {namespace}/{name}: {patch_data}")
        
        logger.info(f"OpenWebUIGroup v1 {namespace}/{name} upserted successfully.")
        return {"status": "upserted"}
    except Exception as e:
        logger.error(f"Failed to upsert group for {namespace}/{name}: {e}")
        raise kopf.TemporaryError(f"Failed to upsert group: {e}", delay=30)


# V2 Handlers (NEW - using existing_secret)
@kopf.on.delete("ops.veitosiander.de", "v2", "OpenWebUIGroup")
def delete_v2(spec, name, namespace, **kwargs):
    group_management = injector.get(GroupManagement)
    
    logger.info(f"Deleting OpenWebUIGroup v2 resource: {namespace}/{name}")
    
    try:
        # Retrieve API key from secret in the same namespace as the CR
        api_key = get_api_key_from_secret(
            spec['existing_secret'],
            namespace
        )
        
        if spec.get('group_id'):
            group_management.delete_group(spec['openwebui_host'], api_key, spec['group_id'])
        else:
            group_management.delete_group_by_name(spec['openwebui_host'], api_key, spec['name'])
        logger.info(f"OpenWebUIGroup v2 {namespace}/{name} deleted successfully.")
    except Exception as e:
        logger.error(f"Failed to delete group {spec['name']}: {e}")
        pass


@kopf.on.create("ops.veitosiander.de", "v2", "OpenWebUIGroup")
@kopf.on.update("ops.veitosiander.de", "v2", "OpenWebUIGroup")
def upsert_v2(spec, name, namespace, **kwargs):
    group_management = injector.get(GroupManagement)
    
    logger.info(f"Upserting OpenWebUIGroup v2 resource: {namespace}/{name}")
    
    try:
        # Retrieve API key from secret in the same namespace as the CR
        api_key = get_api_key_from_secret(
            spec['existing_secret'],
            namespace
        )
        
        group = group_management.upsert_group(
            spec['openwebui_host'],
            api_key,
            spec,
            spec.get('group_id')
        )
        
        # Update is_installed and group_id if needed
        patch_data = {}
        if not spec.get('is_installed', False):
            patch_data["is_installed"] = True
        if group and group.get('id') and group.get('id') != spec.get('group_id'):
            patch_data["group_id"] = group['id']
        
        if patch_data:
            cr = list(kr8s.get("OpenWebUIGroup.ops.veitosiander.de/v2", name, namespace=namespace))[0]
            cr.patch({"spec": patch_data})
            logger.info(f"Updated CRD for {namespace}/{name}: {patch_data}")
        
        logger.info(f"OpenWebUIGroup v2 {namespace}/{name} upserted successfully.")
        return {"status": "upserted"}
    except Exception as e:
        logger.error(f"Failed to upsert group for {namespace}/{name}: {e}")
        raise kopf.TemporaryError(f"Failed to upsert group: {e}", delay=30)
