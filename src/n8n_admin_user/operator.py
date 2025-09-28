from injector import Injector
from kopf import PermanentError
from kubernetes.client import ApiClient
from loguru import logger
import kopf

from src.n8n_admin_user.manager import AdminUserManagement
from src.n8n_admin_user.crd import N8nAdminUser

injector: Injector = None
api: ApiClient = None

def register_handlers(inj: Injector):
    global injector, api
    injector = inj
    api = inj.get(ApiClient)
    logger.info("Registering N8nAdminUser handlers...")
    N8nAdminUser.install(api, exist_ok=True)

@kopf.on.create("ops.veitosiander.de", "v1", "N8nAdminUser")
def create_fn(spec, name, namespace, **kwargs):
    admin_user_management = injector.get(AdminUserManagement)

    logger.info(f"Trying to login to {spec['n8n_domain']} to check if admin user {spec['email']} already exists...")
    auth_cookie = admin_user_management.login(
        domain=spec['n8n_domain'],
        email=spec['email'],
        password=spec['password']
    )
    if auth_cookie:
        logger.info(f"Admin user {spec['email']} already exists for {spec['n8n_domain']}. No action needed.")
        return {"status": "exists"}

    logger.info(f"Creating admin user {spec['email']} for {spec['n8n_domain']}...")
    success = admin_user_management.create_admin_user(
        domain=spec['n8n_domain'],
        email=spec['email'],
        first_name=spec['first_name'],
        last_name=spec['last_name'],
        password=spec['password']
    )

    if success:
        logger.info(f"N8nAdminUser {namespace}/{name} created successfully.")
        return {"status": "created"}
    else:
        raise PermanentError(f"Failed to create admin user for {spec['n8n_domain']}")

@kopf.on.delete("ops.veitosiander.de", "v1", "N8nAdminUser")
def delete_fn(spec, name, namespace, **kwargs):
    logger.info(f"Deleting N8nAdminUser resource: {namespace}/{name}")
    
    # Note: N8N does not provide an API to delete admin users
    # This is a no-op operation as admin user deletion must be done manually
    logger.info(f"N8nAdminUser {namespace}/{name} deleted from Kubernetes. "
                f"Note: Admin user {spec['email']} still exists in N8N at {spec['n8n_domain']} "
                f"and must be removed manually if needed.")
