# Mokey/Hydra OpenID Connect integration for ColdFront

ColdFront django plugin providing Mokey/Hydra OpenID Connect integration for
ColdFront. [Mokey](https://github.com/ubccr/mokey) is self-service account
management portal for [FreeIPA](https://www.freeipa.org). Mokey also supports
the Login/Consent flow for [Hydra](https://github.com/ory/hydra) an OAuth 2.0
and OpenID Connect provider. With this app enabled users are authenticated
using OpenID Connect via Mokey using FreeIPA as the identity provider. User and
group data is automatically updated using information stored in the id\_token
claims.

## Design

This app uses [mozilla-django-oidc](https://github.com/mozilla/mozilla-django-oidc) and
implements a custom backend for connecting OpenID Connect user identities to
Django users.

## Requirements

- uv sync --extra oidc

## Usage
### Mokey/Hydra integration

To enable this plugin set the following environment variables:

```
PLUGIN_AUTH_OIDC=True
PLUGIN_MOKEY=True
OIDC_OP_JWKS_ENDPOINT="https://hydra.local/.well-known/jwks.json"
OIDC_RP_SIGN_ALGO='RS256'
OIDC_RP_CLIENT_ID='coldfront-client-id'
OIDC_RP_CLIENT_SECRET='xxx'
OIDC_OP_AUTHORIZATION_ENDPOINT="https://hydra.local/oauth2/auth"
OIDC_OP_TOKEN_ENDPOINT="https://hydra.local/oauth2/token"
OIDC_OP_USER_ENDPOINT="https://hydra.local/userinfo"
```

### OIDC
If you are just using OIDC and do not need Mokey/Hydra integration: 
- Set the above environment variables, but do not set `PLUGIN_MOKEY`.
- In your [ColdFront configuration file](https://coldfront.readthedocs.io/en/latest/config/#configuration-files) (`local_settings.py` or set by the `COLDFRONT_CONFIG` environment variable), set `SESSION_COOKIE_SAMESITE = "Lax"`
- You may also need to edit `mozilla-django-oidc` [settings](https://mozilla-django-oidc.readthedocs.io/en/stable/settings.html) in your `local_settings.py`.
