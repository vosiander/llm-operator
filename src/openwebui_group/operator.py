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
    if not spec.get('is_installed', False):
        logger.warning(f"group not installed for {namespace}/{name}, skipping reconciliation.")
        return

    logger.info("Pinging Open-WebUI service...")
    group_management = injector.get(GroupManagement)
    if not group_management.ping(spec['openwebui_host']):
        logger.error("Failed to ping Open-WebUI service. Will retry in the next interval.")
        return

    logger.info(f"Reconciling OpenWebUIGroup resource: {namespace}/{name} with spec: {spec}")
    cr = list(kr8s.get("OpenWebUIGroup.ops.veitosiander.de", name, namespace=namespace))[0]

    logger.info(f"Fetched CR: {cr} <- {name}")
    
    # Check by ID first, fall back to name
    group = None
    if spec.get('group_id'):
        group = group_management.get_group_by_id(spec['openwebui_host'], spec['openwebui_api_key'], spec['group_id'])
    
    if group is None:
        group = group_management.get_group_by_name(spec['openwebui_host'], spec['openwebui_api_key'], spec['name'])
    
    if group is not None:
        logger.info(f"Group {spec['name']} exists. Nothing to do...")
    else:
        logger.warning(f"Group {spec['name']} does not exist. Recreating...")
        group = group_management.create_group(spec['openwebui_host'], spec['openwebui_api_key'], spec)
        if group and group.get('id'):
            cr.patch({"spec": {"group_id": group['id']}})
        logger.info(f"Recreated group for {namespace}/{name}")


@kopf.on.delete("ops.veitosiander.de", "v1", "OpenWebUIGroup")
def delete_fn(spec, name, namespace, **kwargs):
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
def create_fn(spec, name, namespace, **kwargs):
    group_management = injector.get(GroupManagement)

    logger.info(f"Creating OpenWebUIGroup resource: {namespace}/{name} with spec: {spec}")

    cr = list(kr8s.get("OpenWebUIGroup.ops.veitosiander.de", name, namespace=namespace))[0]
    logger.info(f"Fetched CR: {cr}")

    try:
        group = group_management.get_group_by_name(spec['openwebui_host'], spec['openwebui_api_key'], spec['name'])
        if group is not None:
            logger.warning(f"Group with name {spec['name']} already exists. Skipping...")
            # Store the group ID even if it already exists
            if group.get('id'):
                cr.patch({"spec": {"group_id": group['id'], "is_installed": True}})
            return {"status": "created"}

        logger.info(f"Creating new group {spec['name']}...")
        group = group_management.create_group(spec['openwebui_host'], spec['openwebui_api_key'], spec)
        logger.info(f"Created group for {namespace}/{name} with name {group.get('name', 'no-name')}, updating CRD...")
        
        # Store the group ID
        patch_data = {"spec": {"is_installed": True}}
        if group.get('id'):
            patch_data["spec"]["group_id"] = group['id']
        cr.patch(patch_data)

        logger.info(f"OpenWebUIGroup {namespace}/{name} created successfully.")
    except Exception as e:
        logger.error(f"Failed to create group for {namespace}/{name}: {e}")
        raise kopf.TemporaryError(f"Failed to create group: {e}", delay=30)

    return {"status": "created"}
