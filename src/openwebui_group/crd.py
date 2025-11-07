import kubecrd
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class OpenWebUIGroupWorkspacePermissions(kubecrd.KubeResourceBase):
    models: bool = field(default=False)
    knowledge: bool = field(default=False)
    prompts: bool = field(default=False)
    tools: bool = field(default=False)


@dataclass
class OpenWebUIGroupChatPermissions(kubecrd.KubeResourceBase):
    file_upload: bool = field(default=False)
    delete: bool = field(default=False)


@dataclass
class OpenWebUIGroupPermissions(kubecrd.KubeResourceBase):
    workspace: OpenWebUIGroupWorkspacePermissions = field(default=None)
    chat: OpenWebUIGroupChatPermissions = field(default=None)


@dataclass
class OpenWebUIGroup(kubecrd.KubeResourceBase):
    __group__ = "ops.veitosiander.de"
    __version__ = "v1"

    openwebui_host: str

    # Group configuration
    name: str
    description: str
    existing_secret: str = field(metadata={"description": "Name of the Kubernetes Secret containing the OpenWebUI API key"})
    
    # Optional fields with defaults
    permissions: OpenWebUIGroupPermissions = field(default=None)
    user_emails: List[str] = field(default_factory=list)
    group_id: str = field(default="")
    is_installed: bool = field(default=False, metadata={"description": "Indicates if the group is installed."})
