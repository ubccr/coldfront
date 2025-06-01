# Example custom LDAP user search for ColdFront

ColdFront plugin providing user searching using LDAP. When adding
users to a allocation or a project, ColdFront will by default look in the
local database only. This app enables searching an LDAP directory. This is just
an example and the code will most likely need to be adapted to your particular
LDAP schema. See the code in utils.py and modify accordingly. Also see the
search.py code in the FreeIPA plugin.

## Design

ColdFront provides an API to define additional user search classes for
extending the default search functionality. This app implements an
`LDAPUserSearch` class in `utils.py` which performs the LDAP search. This class is
then registered with ColdFront by setting `ADDITIONAL_USER_SEARCH_CLASSES`
in `config/plugins/ldap_user_search.py`. This class also allows customization
through Django settings of the attributes requested and how they're mapped to
ColdFront users.

## Requirements

- uv sync --extra ldap

## Usage

To enable this plugin set the following applicable environment variables:

| Option | Default | Description |
| --- | --- | --- |
| `LDAP_USER_SEARCH_SERVER_URI` | N/A | URI for the LDAP server, required |
| `LDAP_USER_SEARCH_BASE` | N/A | Search base, required |
| `LDAP_USER_SEARCH_BIND_DN` | None | Bind DN |
| `LDAP_USER_SEARCH_BIND_PASSWORD` | None | Bind Password |
| `LDAP_USER_SEARCH_CONNECT_TIMEOUT` | 2.5 | Time in seconds before the connection times out |
| `LDAP_USER_SEARCH_USE_SSL` | True | Whether or not to use SSL |
| `LDAP_USER_SEARCH_USE_TLS` | False | Whether or not to use TLS |
| `LDAP_USER_SEARCH_SASL_MECHANISM` | None | One of `"EXTERNAL"`, `"DIGEST-MD5"`, `"GSSAPI"`, or `None` |
| `LDAP_USER_SEARCH_SASL_CREDENTIALS` | None | SASL authorization identity string. If you don't have one and `None` doesn't work, try `""`. |
| `LDAP_USER_SEARCH_PRIV_KEY_FILE` | None | Path to the private key file |
| `LDAP_USER_SEARCH_CERT_FILE` | None | Path to the certificate file |
| `LDAP_USER_SEARCH_CACERT_FILE` | None | Path to the CA certificate file |
| `LDAP_USER_SEARCH_CERT_VALIDATE_MODE` | none | The extent to which the certificate is validated.  Can be 'required' (the certificate is required and validated), 'optional' (certificate is optional but validated if provided), 'none' (certs are ignored) |

The following can be set in your local settings:
| `LDAP_USER_SEARCH_ATTRIBUTE_MAP` | `{"username": "uid", "last_name": "sn", "first_name": "givenName", "email": "mail"}` | A mapping from ColdFront user attributes to LDAP attributes. |
| `LDAP_USER_SEARCH_MAPPING_CALLBACK` | See below. | Function that maps LDAP search results to ColdFront user attributes. See more below. |

`LDAP_USER_SEARCH_MAPPING_CALLBACK` default:
```py
def parse_ldap_entry(attribute_map, entry_dict):
    user_dict = {}
    for user_attr, ldap_attr in attribute_map.items():
        user_dict[user_attr] = entry_dict.get(ldap_attr)[0] if entry_dict.get(ldap_attr) else ''
    return user_dict
```

For custom attributes, set the Django variable `LDAP_USER_SEARCH_ATTRIBUTE_MAP` in ColdFront's [local settings](https://coldfront.readthedocs.io/en/latest/config/#configuration-files). This dictionary maps from ColdFront User attributes to LDAP attributes:
```py
# default
LDAP_USER_SEARCH_ATTRIBUTE_MAP = {
    "username": "uid",
    "last_name": "sn",
    "first_name": "givenName",
    "email": "mail",
}
```

You can also set the attribute to search by through the variable `LDAP_USER_SEARCH_USERNAME_ONLY_ATTR`. This might be useful if you wish to instead search LDAP with an email instead of username.
```py
# this will make the call to search_a_user("john.doe@example.com", "email") search
# for "john.doe@example.com" with the LDAP attribute "mail" if you're using the above map.
LDAP_USER_SEARCH_USERNAME_ONLY_ATTR = "email"
```

To set a custom mapping, define an `LDAP_USER_SEARCH_MAPPING_CALLBACK` function with parameters `attr_map` and `entry_dict` that returns a dictionary mapping ColdFront User attributes to their values. `attr_map` is just `LDAP_USER_SEARCH_ATTRIBUTE_MAP`, and `entry_dict` is further explained below.

For example, if your LDAP schema provides a full name and no first and last name attributes, you can define `LDAP_USER_SEARCH_ATTRIBUTE_MAP` and `LDAP_USER_SEARCH_MAPPING_CALLBACK` as follows:

```py
LDAP_USER_SEARCH_ATTRIBUTE_MAP = {
    "username": "uid",
    "email": "mail",
    "full_name": "cn",
}

def LDAP_USER_SEARCH_MAPPING_CALLBACK(attr_map, entry_dict):
    user_dict = {
        "username": entry_dict.get(attr_map["username"])[0],
        "email": entry_dict.get(attr_map["email"])[0],
        "first_name": entry_dict.get(attr_map["full_name"])[0].split(" ")[0],
        "last_name": entry_dict.get(attr_map["full_name"])[0].split(" ")[-1],
    }
    return user_dict
```

`entry_dict` is provided as a dictionary mapping from the LDAP attribute to a list of values.
```py
entry_dict = {
    'mail': ['jane.emily.doe@example.com'],
    'cn': ['Jane E Doe'],
    'uid': ['janedoe1234']
}
```

If this was the input to the above callback, `user_dict` would look like this:
```py
user_dict = {
    "username": "janedoe1234",
    "email": "jane.emily.doe@example.com",
    "first_name": "Jane",
    "last_name": "Doe",
}
```

## Details
The `search_a_user` function also allows searching for a specific attribute. Providing the `search_by` parameter with a key to the attribute map will have it search for the corresponding attribute.
