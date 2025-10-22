from injector import singleton
from loguru import logger
import requests
import os


@singleton
class KeyManagement:
    def __init__(self):
        pass

    def ping(self, litellm_host: str):
        return requests.get(url=f"{litellm_host}/health/liveness").status_code == 200

    def get_key_by_alias(self, litellm_host: str, litellm_api_key: str, key_alias: str):
        rsp = requests.get(
            url=f"{litellm_host}/key/list?key_alias={key_alias}&return_full_object=true&include_team_keys=true",
            headers={"Authorization": f"Bearer {litellm_api_key}"}
        )

        logger.trace(f"Response from LiteLLM: {rsp.status_code} - {rsp.text}")
        rsp_json = rsp.json()
        if rsp.status_code == 200 and "keys" in rsp_json and len(rsp_json["keys"]) > 0:
            return rsp_json["keys"][0]

        return None

    def delete_key(self, litellm_host: str, litellm_api_key: str, key_alias):
        del_rsp = requests.post(
            url=f"{litellm_host}/key/delete",
            headers={"Authorization": f"Bearer {litellm_api_key}"},
            json={"key_aliases": [key_alias]}
        )

        if del_rsp.status_code == 200:
            logger.info(f"Deleted existing key with alias {key_alias}")
        else:
            logger.error(f"Failed to delete existing key: {del_rsp.status_code} - {del_rsp.text}")
            raise ValueError(f"Failed to delete existing key: {del_rsp.status_code} - {del_rsp.text}")

    def generate_key(self, litellm_host: str, litellm_api_key: str, user_id: str, key_alias: str, key_name: str, team_id: str, models=None):
        if models is None:
            models = []

        if type(models) is not list:
            raise ValueError("models must be a list of model names")

        data = {
            "user_id": user_id,
            "key_alias": key_alias,
            "key_name": key_name,
            "models": models
        }
        if team_id and team_id != "":
            data["team_id"] = team_id

        rsp = requests.post(
            url=f"{litellm_host}/key/generate",
            headers={"Authorization": f"Bearer {litellm_api_key}"},
            json=data
        )
        logger.trace(f"Response from LiteLLM: {rsp.status_code} - {rsp.text}")

        rsp_json = rsp.json()
        logger.trace(f"Response JSON: {rsp_json}")
        if rsp.status_code != 200:
            logger.error(f"Failed to generate key: {rsp.status_code} - {rsp.text}")
            raise ValueError(f"Failed to generate key: {rsp.status_code} - {rsp.text}")

        return rsp_json["key"]