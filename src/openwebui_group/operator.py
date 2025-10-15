from injector import Injector
from kubernetes.client import ApiClient
from loguru import logger
import kopf
import kr8s

from src.openwebui_group.manager import GroupManagement
from src.openwebui_group.crd import OpenWebUIGroup

injector: Injector = None
api: ApiClient = None


def register_handlers(inj: Injector):
    global injector, api
    injector = inj
    api = inj.get(ApiClient)
    logger.info("Registering OpenWebUIGroup handlers...")
    OpenWebUIGroup.install(api, exist_ok=True)


@kopf.on.timer("ops.veitosiander.de", "v1", "OpenWebUIGroup", interval=30)
def timer_fn(spec, name, namespace, **kwargs):
    api_key = spec.get('openwebui_api_key', '').strip()
    
    if not api_key:
        logger.debug(f"No API key for {namespace}/{name}, skipping reconciliation.")
        return

    logger.info("Pinging Open-WebUI service...")
    group_management = injector.get(GroupManagement)
    if not group_management.ping(spec['openwebui_host']):
        logger.error("Failed to ping Open-WebUI service. Will retry in the next interval.")
        return

    logger.info(f"Reconciling OpenWebUIGroup resource: {namespace}/{name} with spec: {spec}")
    cr = list(kr8s.get("OpenWebUIGroup.ops.veitosiander.de", name, namespace=namespace))[0]

    logger.info(f"Fetched CR: {cr} <- {name}")
    group = group_management.upsert_group(spec['openwebui_host'], spec['openwebui_api_key'], spec, spec.get('group_id'))
    
    # Update group_id if it changed
    if group and group.get('id') and group['id'] != spec.get('group_id'):
        cr.patch({"spec": {"group_id": group['id']}})
    
    logger.info(f"Upserted group {spec['name']} for {namespace}/{name}")


@kopf.on.delete("ops.veitosiander.de", "v1", "OpenWebUIGroup")
def delete_fn(spec, name, namespace, **kwargs):
    api_key = spec.get('openwebui_api_key', '').strip()
    
    if not api_key:
        logger.info(f"No API key for {namespace}/{name}, nothing to delete.")
        return
    
    group_management = injector.get(GroupManagement)

    logger.info(f"Deleting OpenWebUIGroup resource: {namespace}/{name} with spec: {spec}")
    try:
        if spec.get('group_id'):
            group_management.delete_group(spec['openwebui_host'], spec['openwebui_api_key'], spec['group_id'])
        else:
            group_management.delete_group_by_name(spec['openwebui_host'], spec['openwebui_api_key'], spec['name'])
        logger.info(f"OpenWebUIGroup {namespace}/{name} deleted successfully.")
    except Exception as e:
        logger.error(f"Failed to delete group {spec['name']}: {e}")
        pass


@kopf.on.create("ops.veitosiander.de", "v1", "OpenWebUIGroup")
@kopf.on.update("ops.veitosiander.de", "v1", "OpenWebUIGroup")
def upsert_fn(spec, name, namespace, **kwargs):
    api_key = spec.get('openwebui_api_key', '').strip()
    
    if not api_key:
        logger.info(f"No API key for {namespace}/{name}, skipping upsert.")
        return {"status": "waiting_for_api_key"}
    
    group_management = injector.get(GroupManagement)
    
    logger.info(f"Upserting OpenWebUIGroup resource: {namespace}/{name}")
    
    try:
        group = group_management.upsert_group(
            spec['openwebui_host'],
            spec['openwebui_api_key'],
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
            cr = list(kr8s.get("OpenWebUIGroup.ops.veitosiander.de", name, namespace=namespace))[0]
            cr.patch({"spec": patch_data})
            logger.info(f"Updated CRD for {namespace}/{name}: {patch_data}")
        
        logger.info(f"OpenWebUIGroup {namespace}/{name} upserted successfully.")
        return {"status": "upserted"}
    except Exception as e:
        logger.error(f"Failed to upsert group for {namespace}/{name}: {e}")
        raise kopf.TemporaryError(f"Failed to upsert group: {e}", delay=30)
