import kubecrd
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class LiteLLMTeam(kubecrd.KubeResourceBase):
    __group__ = 'ops.veitosiander.de'
    __version__ = 'v1'

    litellm_host: str
    litellm_api_key: str
    team_name: str
    models: List[str] = field(default_factory=list)
    max_budget: float = field(default=None)
    budget_duration: str = field(default=None)
    team_id: str = field(default="", metadata={"description": "The team ID returned by LiteLLM."})
    key_value: str = field(default="", metadata={"description": "The generated API key for the team."})
