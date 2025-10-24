import kubecrd
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class OpenWebUIPromptAccessControl(kubecrd.KubeResourceBase):
    read: list[str]
    write: list[str]


@dataclass
class OpenWebUIPrompt(kubecrd.KubeResourceBase):
    __group__ = "ops.veitosiander.de"
    __version__ = "v1"

    openwebui_host: str

    # Prompt configuration
    command: str  # unique identifier
    title: str
    content: str
    existing_secret: str = field(metadata={"description": "Name of the Kubernetes Secret containing the OpenWebUI API key in the same namespace as this resource"})
    
    # Optional fields with defaults
    is_installed: bool = field(default=False, metadata={"description": "Indicates if the prompt is installed."})
