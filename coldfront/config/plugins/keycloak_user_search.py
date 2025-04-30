from coldfront.config.env import ENV

# ----------------------------------------------------------------------------
#  This enables searching for users via Keycloak
# ----------------------------------------------------------------------------

KEYCLOAK_BASE_URL = ENV.str("KEYCLOAK_BASE_URL", default="https://sso.hpc.nyu.edu/")

KEYCLOAK_USERNAME = ENV.str("KEYCLOAK_USERNAME")
KEYCLOAK_PASSWORD = ENV.str("KEYCLOAK_PASSWORD")
KEYCLOAK_CLIENT_ID = ENV.str("KEYCLOAK_CLIENT_ID")
KEYCLOAK_CLIENT_SECRET = ENV.str("KEYCLOAK_CLIENT_SECRET")

ADDITIONAL_USER_SEARCH_CLASSES = [
    "coldfront.plugins.keycloak_user_search.search.KeycloakUserSearch"
]
