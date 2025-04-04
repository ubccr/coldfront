from dataclasses import dataclass
from coldfront.core.utils.common import import_from_settings
from httpx import URL


@dataclass
class KeycloakClientConfig:
    base_url: URL = URL(import_from_settings("KEYCLOAK_BASE_URL"))
    username: str = import_from_settings("KEYCLOAK_USERNAME")
    password: str = import_from_settings("KEYCLOAK_PASSWORD")
    client_id: str = import_from_settings("KEYCLOAK_CLIENT_ID")
    client_secret: str = import_from_settings("KEYCLOAK_CLIENT_SECRET")
    token_path: str = "realms/hpc/protocol/openid-connect/token"
    search_path: str = "admin/realms/hpc/users?search="
    search_username_path: str = "admin/realms/hpc/users?username="
