import kubecrd
from dataclasses import dataclass, field


@dataclass
class UptimeKumaSetup(kubecrd.KubeResourceBase):
    __group__ = "ops.veitosiander.de"
    __version__ = "v1"

    # Required fields
    kuma_url: str = field(metadata={"description": "Uptime Kuma instance URL (e.g., https://uptime.example.com)"})
    existing_secret: str = field(metadata={"description": "Name of Kubernetes Secret containing username and password keys in same namespace"})
    
    # Status field
    is_setup: bool = field(default=False, metadata={"description": "Setup status of Uptime Kuma instance"})
