from injector import Injector
from kubernetes.client import ApiClient
from loguru import logger
import kopf
import kr8s

from src.litellm_key.manager import KeyManagement
from src.litellm_team.crd import LiteLLMTeam
from src.litellm_team.manager import TeamManagement

injector: Injector = None
api: ApiClient = None


def register_handlers(inj: Injector):
    global injector, api
    injector = inj
    api = inj.get(ApiClient)
    logger.info("Registering LiteLLMTeam handlers...")
    LiteLLMTeam.install(api, exist_ok=True)


@kopf.on.delete("ops.veitosiander.de", "v1", "LiteLLMTeam")
def delete_fn(spec, name, namespace, **kwargs):
    team_management = injector.get(TeamManagement)

    logger.info(f"Deleting LiteLLMTeam resource: {namespace}/{name} with spec: {spec}")

    # Only delete if team_id exists
    if spec.get("team_id") and spec["team_id"] != "":
        try:
            # Delete the team's API key first
            logger.info(f"Deleting team key with alias {spec['team_name']}")
            team_management.delete_team_key(spec["litellm_host"], spec["litellm_api_key"], spec['team_name'])

            # Then delete the team
            team_management.delete_team(spec["litellm_host"], spec["litellm_api_key"], spec["team_id"])
            logger.info(f"LiteLLMTeam {namespace}/{name} deleted successfully.")
        except Exception as e:
            logger.error(f"Failed to delete team {spec['team_id']}: {e}")
            pass
    else:
        logger.warning(f"Team ID not set for {namespace}/{name}, skipping deletion.")


@kopf.on.update("ops.veitosiander.de", "v1", "LiteLLMTeam")
@kopf.on.create("ops.veitosiander.de", "v1", "LiteLLMTeam")
def create_fn(spec, name, namespace, **kwargs):
    team_management = injector.get(TeamManagement)
    key_management = injector.get(KeyManagement)

    logger.info(f"Creating LiteLLMTeam resource: {namespace}/{name} with spec: {spec}")

    cr = list(kr8s.get("LiteLLMTeam.ops.veitosiander.de", name, namespace=namespace))[0]
    logger.info(f"Fetched CR: {cr}")

    try:
        # Check if team already exists
        team = team_management.get_team_by_name(spec["litellm_host"], spec["litellm_api_key"], spec["team_name"])

        if team is None:
            # Create new team
            logger.info(f"Creating new team {spec['team_name']}...")
            result = team_management.create_team(
                spec["litellm_host"],
                spec["litellm_api_key"],
                spec["team_name"],
                spec.get("max_budget"),
                spec.get("budget_duration")
            )
            logger.info(f"Created team: {result}")
            team_id = result.get("team_id")
            logger.info(f"Created team with ID {team_id}")
        else:
            team_id = team.get("team_id")

        logger.info(f"Updating team {spec['team_name']} with ID {team_id}...")
        team_management.update_team(
            spec["litellm_host"],
            spec["litellm_api_key"],
            team_id,
            spec["team_name"],
            spec.get("models", []),
            spec.get("max_budget"),
            spec.get("budget_duration")
        )
        logger.info(f"Updated existing team {spec['team_name']}")

        # Add models to team
        if spec.get("models"):
            logger.info(f"Adding models {spec['models']} to team...")
            team_management.add_models_to_team(
                spec["litellm_host"],
                spec["litellm_api_key"],
                team_id,
                spec["models"]
            )

        key_obj = key_management.get_key_by_alias(
            spec["litellm_host"],
            spec["litellm_api_key"],
            spec["team_name"]
        )
        cr_spec = {"team_id": team_id}
        if key_obj is None:
            logger.info(f"Generating new key for team {spec['team_name']}...")
            cr_spec["key_value"] = team_management.generate_team_key(
                spec["litellm_host"],
                spec["litellm_api_key"],
                team_id,
                key_alias=spec["team_name"],
            )
        else:
            logger.info(f"Key already exists for team {spec['team_name']}...")

        logger.info(f"Updating CR with team_id {team_id}...")
        cr.patch({"spec": cr_spec})

        logger.info(f"LiteLLMTeam {namespace}/{name} created successfully.")
    except Exception as e:
        logger.error(f"Failed to create team for {namespace}/{name}: {e}")
        raise kopf.TemporaryError(f"Failed to create team: {e}", delay=30)

    return {"status": "created"}
