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

    openwebui_api_key: str = field(default="", metadata={"description": "Optional: API key for authentication. If not provided, the operator will attempt to use other authentication methods"})
    is_installed: bool = field(default=False, metadata={"description": "Indicates if the prompt is installed."})
