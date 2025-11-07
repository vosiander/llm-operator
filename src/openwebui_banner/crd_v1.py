import kubecrd
from dataclasses import dataclass, field

@dataclass
class OpenWebUIBannerV1(kubecrd.KubeResourceBase):
    __group__ = "ops.veitosiander.de"
    __version__ = "v1"

    # Required fields
    openwebui_host: str
    id: str
    type: str
    content: str
    
    # Optional fields with defaults
    dismissible: bool = field(default=True)
    timestamp: int = field(default=0)
    title: str = field(default="")
    openwebui_api_key: str = field(default="", metadata={"description": "DEPRECATED: API key for authentication. Please migrate to v2 using existing_secret field"})
    is_installed: bool = field(default=False, metadata={"description": "Indicates if the banner is installed."})
