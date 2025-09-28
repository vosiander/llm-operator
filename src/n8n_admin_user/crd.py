import kubecrd
from dataclasses import dataclass

@dataclass
class N8nAdminUser(kubecrd.KubeResourceBase):
    __group__ = 'ops.veitosiander.de'
    __version__ = 'v1'

    n8n_domain: str
    email: str
    first_name: str
    last_name: str
    password: str
