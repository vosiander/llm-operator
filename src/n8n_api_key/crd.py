import kubecrd
from dataclasses import dataclass, field

@dataclass
class N8nApiKey(kubecrd.KubeResourceBase):
    __group__ = 'ops.veitosiander.de'
    __version__ = 'v1'

    n8n_domain: str
    email: str
    password: str
    api_key_name: str
    secret_name: str
    secret_namespace: str = field(default="default")
    n8n_api_key_name: str = field(default="")  # Auto-populated with unique label
    user_id: str = field(default="")           # Auto-populated with N8N user ID
    api_key_id: str = field(default="")        # Auto-populated with N8N API key ID (needed for deletion)
