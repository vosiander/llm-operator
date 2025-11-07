import kubecrd
from dataclasses import dataclass, field

@dataclass
class OpenWebUIBannerV2(kubecrd.KubeResourceBase):
    __group__ = "ops.veitosiander.de"
    __version__ = "v2"

    # Required fields
    openwebui_host: str
    id: str
    type: str
    content: str
    existing_secret: str = field(metadata={"description": "Name of the Kubernetes Secret containing the OpenWebUI API key in the same namespace as this resource"})
    
    # Optional fields with defaults
    dismissible: bool = field(default=True)
    timestamp: int = field(default=0)
    title: str = field(default="")
    is_installed: bool = field(default=False, metadata={"description": "Indicates if the banner is installed."})
