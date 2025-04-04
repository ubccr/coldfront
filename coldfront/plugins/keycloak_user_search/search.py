from coldfront.core.user.utils import UserSearch
from coldfront.plugins.keycloak_user_search.keycloak_config import KeycloakClientConfig
import logging
from httpx import Client, URL, Headers

logger = logging.getLogger(__name__)


class KeycloakClient:
    def __init__(self):
        self.config: KeycloakClientConfig = KeycloakClientConfig()
        self.token: str = str()
        self.client: Client = Client()

    def get_access_token(self) -> None:
        token_url: URL = self.config.base_url.join(self.config.token_path)
        data = {
            "username": self.config.username,
            "password": self.config.password,
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
            "grant_type": "password",
        }
        logger.info(f"base_url is: {self.config.base_url}")
        logger.info(f"token_url is : {token_url}")
        resp = self.client.post(token_url, data=data).raise_for_status()
        self.token = resp.json()["access_token"]
        return

    def get_all_fields_matches(self, input_str: str) -> list[dict]:
        headers = Headers(
            {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.token}",
            }
        )
        search_url = self.config.base_url.join(self.config.search_path + input_str)
        result = self.client.get(search_url, headers=headers).raise_for_status().json()
        return result

    def get_username_matches(self, input_str: str) -> list[dict]:
        headers = Headers(
            {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.token}",
            }
        )
        search_url = self.config.base_url.join(
            self.config.search_username_path + input_str
        )
        result = self.client.get(search_url, headers=headers).raise_for_status().json()
        return result


class KeycloakUserSearch(UserSearch):
    search_source = "Keycloak"

    def __init__(self, *args, **kwargs):
        self.keycloak_client = KeycloakClient()
        super().__init__(*args, **kwargs)

    def search_a_user(self, user_search_string=None, search_by="all_fields"):
        self.keycloak_client.get_access_token()
        matches: list[dict] = []
        if search_by == "all_fields":
            matches = self.keycloak_client.get_all_fields_matches(user_search_string)
        elif search_by == "username_only":
            matches = self.keycloak_client.get_username_matches(user_search_string)
        else:
            raise ValueError("search_by must be one of all_fields, username_only")

        if matches == []:
            logger.info("Keycloak-user-search: No matchig users found!")

        return [
            {
                "username": match["username"],
                "last_name": match.get("lastName", ""),
                "first_name": match.get("firstName", ""),
                "email": match.get("email", ""),
                "source": self.search_source,
            }
            for match in matches
        ]
