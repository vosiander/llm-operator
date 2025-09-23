import kubecrd
from dataclasses import dataclass, field
from typing import List

@dataclass
class LiteLLMParams(kubecrd.KubeResourceBase):
    input_cost_per_token: float = 0
    output_cost_per_token: float = 0
    input_cost_per_second: float = 0
    output_cost_per_second: float = 0
    input_cost_per_pixel: float = 0
    output_cost_per_pixel: float = 0
    api_key: str = field(default=None)
    api_base: str = field(default=None)
    api_version: str = field(default=None)
    vertex_project: str = field(default=None)
    vertex_location: str = field(default=None)
    vertex_credentials: str = field(default=None)
    region_name: str = field(default=None)
    aws_access_key_id: str = field(default=None)
    aws_secret_access_key: str = field(default=None)
    aws_region_name: str = field(default=None)
    watsonx_region_name: str = field(default=None)
    custom_llm_provider: str = field(default=None)
    tpm: int = 0
    rpm: int = 0
    timeout: float = 0
    stream_timeout: float = 0
    max_retries: int = 0
    organization: str = field(default=None)
    configurable_clientside_auth_params: List[str] = field(default_factory=list)
    litellm_credential_name: str = field(default=None)
    litellm_trace_id: str = field(default=None)
    max_file_size_mb: float = 0
    max_budget: float = 0
    budget_duration: str = field(default=None)
    use_in_pass_through: bool = False
    use_litellm_proxy: bool = False
    merge_reasoning_content_in_choices: bool = False
    mock_response: str = field(default=None)
    auto_router_config_path: str = field(default=None)
    auto_router_config: str = field(default=None)
    auto_router_default_model: str = field(default=None)
    auto_router_embedding_model: str = field(default=None)
    model: str = field(default=None)

@dataclass
class LiteLLMModelInfo(kubecrd.KubeResourceBase):
    id: str = field(default=None)
    db_model: bool = False
    updated_at: str = field(default=None)
    updated_by: str = field(default=None)
    created_at: str = field(default=None)
    created_by: str = field(default=None)
    base_model: str = field(default=None)
    tier: str = field(default="paid")
    team_id: str = field(default=None)
    team_public_model_name: str = field(default=None)

@dataclass
class LiteLLMModel(kubecrd.KubeResourceBase):
    __group__ = "ops.veitosiander.de"
    __version__ = "v1"

    litellm_host: str
    litellm_api_key: str

    model_name: str
    litellm_params: LiteLLMParams = field(metadata={"description": "LiteLLM parameters for the model."})
    model_info: LiteLLMModelInfo = field(metadata={"description": "Information about the model."})

    is_installed: bool = field(default=False, metadata={"description": "Indicates if the model is installed."})
