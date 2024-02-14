# MyBRC / MyLRC REST API

The service's REST API is located at `/api`.

## Getting a Token

Some endpoints require an authorization token, which can be retrieved:

1. From an API endpoint, using username and password (not recommended over
HTTP):<br><br>

   Make a `POST` request to `/api/api_token_auth/` with body:

   ```
   {
       "username": "username",
       "password": "password",
   }
   ```

   This will return a response containing the requested user's token. Note that
the token displayed below is not valid.

   ```
   {
       "token": "c99b5142a126796ff03454f475b0381736793a1f"
   }
   ```

2. For developers, from the Django shell:

   ```
   from coldfront.core.user.models import ExpiringToken
   from django.contrib.auth.models import User

   username = "username"
   user = User.objects.get(username=username)
   ExpiringToken.objects.create(user=user)
   ```

## Authorizing a Request

For those endpoints requiring an authorization token, it must be provided in
the request headers. Note that this is exposed when not using HTTPS.

```
{
    "Authorization": "Token c99b5142a126796ff03454f475b0381736793a1f",
}
```

### cURL Example

```
curl --header "Authorization: Token c99b5142a126796ff03454f475b0381736793a1f" https://domain.tld/api/
```

## Limiting Write Access

Some methods (i.e., `POST`, `PUT`, `PATCH`) may only be accessible to
superusers. For these, the provided authorization token must belong to a user
with `is_superuser` set to `True`.

## Limiting Access by IP

Access to the API may be limited by IP range. This can be configured in
Ansible, via the `ip_range_with_api_access` variable.
