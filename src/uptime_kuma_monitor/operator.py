from injector import Injector
from kubernetes.client import ApiClient
from loguru import logger
import kopf
import kr8s
import base64

from src.uptime_kuma_monitor.manager import MonitorManagement
from src.uptime_kuma_monitor.crd import UptimeKumaMonitor

injector: Injector = None
api: ApiClient = None


def get_credentials_from_secret(secret_name: str, secret_namespace: str) -> tuple[str, str]:
    """Retrieve username and password from Kubernetes Secret.
    
    Args:
        secret_name: Name of the secret
        secret_namespace: Namespace of the secret
        
    Returns:
        tuple: (username, password)
        
    Raises:
        ValueError: If secret not found or missing required keys
    """
    try:
        secrets = list(kr8s.get("secrets", secret_name, namespace=secret_namespace))
        if not secrets:
            raise ValueError(f"Secret {secret_name} not found in namespace {secret_namespace}")
        
        secret = secrets[0]
        username_b64 = secret.data.get('username')
        password_b64 = secret.data.get('password')
        
        if not username_b64:
            raise ValueError(f"Secret {secret_name} does not contain 'username' key")
        if not password_b64:
            raise ValueError(f"Secret {secret_name} does not contain 'password' key")
        
        username = base64.b64decode(username_b64).decode('utf-8')
        password = base64.b64decode(password_b64).decode('utf-8')
        return username, password
    except Exception as e:
        logger.error(f"Failed to retrieve credentials from secret {secret_namespace}/{secret_name}: {e}")
        raise


def register_handlers(inj: Injector):
    global injector, api
    injector = inj
    api = inj.get(ApiClient)
    logger.info("Registering UptimeKumaMonitor handlers...")
    UptimeKumaMonitor.install(api, exist_ok=True)


@kopf.on.create("ops.veitosiander.de", "v1", "UptimeKumaMonitor")
@kopf.on.update("ops.veitosiander.de", "v1", "UptimeKumaMonitor")
def upsert_monitor(spec, name, namespace, **kwargs):
    monitor_management = injector.get(MonitorManagement)
    
    logger.info(f"Upserting UptimeKumaMonitor: {namespace}/{name}")
    
    kuma_api = None
    try:
        # Retrieve credentials from secret in the same namespace as the CR
        username, password = get_credentials_from_secret(
            spec['existing_secret'],
            namespace
        )
        
        # Connect to Uptime Kuma
        kuma_api = monitor_management.connect_to_kuma(
            spec['kuma_url'],
            username,
            password
        )
        
        # Build monitor configuration
        monitor_config = monitor_management.build_monitor_config(spec)
        
        # Upsert monitor
        monitor_id = spec.get('monitor_id', 0)
        result = monitor_management.upsert_monitor(kuma_api, monitor_id, monitor_config)
        
        # Extract monitor ID from result
        new_monitor_id = result.get('monitorID', monitor_id)
        
        # Update status fields if needed
        needs_update = False
        updates = {}
        
        if new_monitor_id != spec.get('monitor_id', 0):
            updates['monitor_id'] = new_monitor_id
            needs_update = True
        
        if not spec.get('is_installed', False):
            updates['is_installed'] = True
            needs_update = True
        
        if needs_update:
            cr = list(kr8s.get("UptimeKumaMonitor.ops.veitosiander.de/v1", name, namespace=namespace))[0]
            cr.patch({"spec": updates})
            logger.info(f"Updated status fields for {namespace}/{name}: {updates}")
        
        logger.info(f"UptimeKumaMonitor {namespace}/{name} upserted successfully with ID {new_monitor_id}")
        return {"status": "upserted", "monitor_id": new_monitor_id}
        
    except ValueError as e:
        logger.error(f"Failed to retrieve credentials for {namespace}/{name}: {e}")
        raise kopf.TemporaryError(f"Failed to retrieve credentials: {e}", delay=30)
    except Exception as e:
        logger.error(f"Failed to upsert monitor for {namespace}/{name}: {e}")
        raise kopf.TemporaryError(f"Failed to upsert monitor: {e}", delay=30)
    finally:
        if kuma_api:
            monitor_management.disconnect_api(kuma_api)


@kopf.on.delete("ops.veitosiander.de", "v1", "UptimeKumaMonitor")
def delete_monitor(spec, name, namespace, **kwargs):
    monitor_management = injector.get(MonitorManagement)
    
    logger.info(f"Deleting UptimeKumaMonitor resource: {namespace}/{name}")
    
    monitor_id = spec.get('monitor_id', 0)
    if monitor_id == 0:
        logger.info(f"No monitor_id for {namespace}/{name}, nothing to delete from Uptime Kuma.")
        return
    
    kuma_api = None
    try:
        # Retrieve credentials from secret in the same namespace as the CR
        username, password = get_credentials_from_secret(
            spec['existing_secret'],
            namespace
        )
        
        # Connect to Uptime Kuma
        kuma_api = monitor_management.connect_to_kuma(
            spec['kuma_url'],
            username,
            password
        )
        
        # Delete monitor
        monitor_management.delete_monitor(kuma_api, monitor_id)
        logger.info(f"UptimeKumaMonitor {namespace}/{name} deleted successfully from Uptime Kuma.")
        
    except Exception as e:
        logger.error(f"Failed to delete monitor {monitor_id} for {namespace}/{name}: {e}")
        # Don't raise exception on delete to allow cleanup to proceed
        pass
    finally:
        if kuma_api:
            monitor_management.disconnect_api(kuma_api)
