from injector import singleton
from loguru import logger
import requests
from typing import Dict, Optional, List, Any


@singleton
class TeamManagement:
    def __init__(self):
        pass

    def ping(self, litellm_host: str) -> bool:
        """Check if LiteLLM service is available."""
        try:
            response = requests.get(url=f"{litellm_host}/health/liveness")
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Failed to ping LiteLLM service: {e}")
            return False

    def get_team_by_name(self, litellm_host: str, litellm_api_key: str, team_name: str) -> Optional[Dict[str, Any]]:
        """Get team information by team name (alias)."""
        try:
            response = requests.get(
                url=f"{litellm_host}/team/list",
                headers={"Authorization": f"Bearer {litellm_api_key}"}
            )

            logger.trace(f"List teams response: {response.status_code} - {response.text}")

            if response.status_code == 200:
                teams_data = response.json()
                # Look for team with matching team_alias
                if isinstance(teams_data, list):
                    for team in teams_data:
                        if team.get("team_alias") == team_name:
                            return team
                elif isinstance(teams_data, dict) and "teams" in teams_data:
                    for team in teams_data["teams"]:
                        if team.get("team_alias") == team_name:
                            return team

                logger.info(f"Team with name {team_name} not found")
                return None
            else:
                logger.error(f"Failed to list teams: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"Exception while getting team by name {team_name}: {e}")
            return None

    def create_team(self, litellm_host: str, litellm_api_key: str, team_name: str,
                    max_budget: Optional[float] = None, budget_duration: Optional[str] = None) -> Dict[str, Any]:
        """Create a new team."""
        try:
            team_data = {
                "team_alias": team_name
            }

            # Add budget configuration if provided
            if max_budget is not None:
                team_data["max_budget"] = str(max_budget)
            if budget_duration is not None:
                team_data["budget_duration"] = budget_duration

            logger.trace(f"Creating team with data: {team_data}")
            response = requests.post(
                url=f"{litellm_host}/team/new",
                headers={"Authorization": f"Bearer {litellm_api_key}"},
                json=team_data
            )

            logger.trace(f"Create team response: {response.status_code} - {response.text}")

            if response.status_code == 200:
                result = response.json()
                logger.info(f"Successfully created team {team_name}")
                return result
            else:
                logger.error(f"Failed to create team: {response.status_code} - {response.text}")
                raise ValueError(f"Failed to create team: {response.status_code} - {response.text}")

        except Exception as e:
            logger.error(f"Exception while creating team: {e}")
            raise

    def update_team(self, litellm_host: str, litellm_api_key: str, team_id: str,
                    team_name: str, models: List[str], max_budget: Optional[float] = None,
                    budget_duration: Optional[str] = None) -> Dict[str, Any]:
        """Update an existing team."""
        try:
            team_data = {
                "team_id": team_id,
                "team_alias": team_name,
                "models": models
            }

            # Add budget configuration if provided
            if max_budget is not None:
                team_data["max_budget"] = max_budget
            if budget_duration is not None:
                team_data["budget_duration"] = budget_duration

            logger.trace(f"Updating team with data: {team_data}")
            response = requests.post(
                url=f"{litellm_host}/team/update",
                headers={"Authorization": f"Bearer {litellm_api_key}"},
                json=team_data
            )

            logger.trace(f"Update team response: {response.status_code} - {response.text}")

            if response.status_code == 200:
                result = response.json()
                logger.info(f"Successfully updated team {team_id}")
                return result
            else:
                logger.error(f"Failed to update team: {response.status_code} - {response.text}")
                raise ValueError(f"Failed to update team: {response.status_code} - {response.text}")

        except Exception as e:
            logger.error(f"Exception while updating team: {e}")
            raise

    def add_models_to_team(self, litellm_host: str, litellm_api_key: str, team_id: str, models: List[str]) -> None:
        """Add model permissions to a team."""
        try:
            logger.trace(f"Adding model {",".join(models)} to team {team_id}")
            response = requests.post(
                url=f"{litellm_host}/team/model/add",
                headers={"Authorization": f"Bearer {litellm_api_key}"},
                json={
                    "team_id": team_id,
                    "models": models
                }
            )

            logger.trace(f"Add model response: {response.status_code} - {response.text}")

            if response.status_code == 200:
                logger.info(f"Successfully added model {",".join(models)} to team {team_id}")
            else:
                logger.warning(f"Failed to add model {",".join(models)} to team: {response.status_code} - {response.text}")

        except Exception as e:
            logger.error(f"Exception while adding models to team: {e}")
            raise

    def generate_team_key(self, litellm_host: str, litellm_api_key: str, team_id: str, key_alias: str) -> str:
        """Generate an API key for a team."""
        try:
            key_data = {
                "team_id": team_id,
                "key_alias": key_alias
            }

            logger.trace(f"Generating key for team {team_id} with alias {key_alias}")
            response = requests.post(
                url=f"{litellm_host}/key/generate",
                headers={"Authorization": f"Bearer {litellm_api_key}"},
                json=key_data
            )

            logger.trace(f"Generate key response: {response.status_code} - {response.text}")

            if response.status_code == 200:
                result = response.json()
                key_value = result.get("key")
                logger.info(f"Successfully generated key for team {team_id}")
                return key_value
            else:
                logger.error(f"Failed to generate key: {response.status_code} - {response.text}")
                raise ValueError(f"Failed to generate key: {response.status_code} - {response.text}")

        except Exception as e:
            logger.error(f"Exception while generating team key: {e}")
            raise

    def delete_team_key(self, litellm_host: str, litellm_api_key: str, key_alias: str) -> None:
        """Delete an API key by alias."""
        try:
            logger.trace(f"Deleting key with alias {key_alias}")
            response = requests.post(
                url=f"{litellm_host}/key/delete",
                headers={"Authorization": f"Bearer {litellm_api_key}"},
                json={"key_aliases": [key_alias]}
            )

            logger.trace(f"Delete key response: {response.status_code} - {response.text}")

            if response.status_code == 200:
                logger.info(f"Successfully deleted key with alias {key_alias}")
            else:
                logger.warning(f"Failed to delete key with alias {key_alias}: {response.status_code} - {response.text}")
                # Don't raise exception - key might not exist

        except Exception as e:
            logger.warning(f"Exception while deleting key {key_alias}: {e}")
            # Don't raise exception - allow team deletion to proceed

    def delete_team(self, litellm_host: str, litellm_api_key: str, team_id: str) -> None:
        """Delete a team."""
        try:
            team_data = {
                "team_ids": [team_id]
            }

            logger.trace(f"Deleting team {team_id}")
            response = requests.post(
                url=f"{litellm_host}/team/delete",
                headers={"Authorization": f"Bearer {litellm_api_key}"},
                json=team_data
            )

            logger.trace(f"Delete team response: {response.status_code} - {response.text}")

            if response.status_code == 200:
                logger.info(f"Successfully deleted team {team_id}")
            else:
                logger.error(f"Failed to delete team: {response.status_code} - {response.text}")
                raise ValueError(f"Failed to delete team: {response.status_code} - {response.text}")

        except Exception as e:
            logger.error(f"Exception while deleting team: {e}")
            raise
