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

- pip install mozilla-django-oidc

## Usage

To enable this plugin add or uncomment the following in your
local\_settings.py file:

```
    EXTRA_APPS += [
        'mozilla_django_oidc',
        'coldfront.plugins.mokey_oidc',
    ]

    EXTRA_AUTHENTICATION_BACKENDS += [
        'coldfront.plugins.mokey_oidc.auth.OIDCMokeyAuthenticationBackend',
    ]

    EXTRA_MIDDLEWARE += [
        'mozilla_django_oidc.middleware.SessionRefresh',
    ]

    OIDC_OP_JWKS_ENDPOINT = "https://hydra.local/.well-known/jwks.json"
    OIDC_RP_SIGN_ALGO = 'RS256'
    OIDC_RP_CLIENT_ID = 'coldfront-client-id'
    OIDC_RP_CLIENT_SECRET = 'xxx'
    OIDC_OP_AUTHORIZATION_ENDPOINT = "https://hydra.local/oauth2/auth"
    OIDC_OP_TOKEN_ENDPOINT = "https://hydra.local/oauth2/token"
    OIDC_OP_USER_ENDPOINT = "https://hydra.local/userinfo"

    # Optional config settings
    MOKEY_OIDC_PI_GROUP = 'pi'
    MOKEY_OIDC_ALLOWED_GROUPS = ['academic']
    MOKEY_OIDC_DENY_GROUPS = ['badguys']
```
