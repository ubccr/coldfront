# Example custom LDAP user search for ColdFront

ColdFront plugin providing user searching using LDAP. When adding
users to a allocation or a project, ColdFront will by default look in the
local database only. This app enables searching an LDAP directory. This is just
an example and the code will most likely need to be adapted to your particular
LDAP schema. See the code in utils.py and modify accordingly. Also see the
search.py code in the FreeIPA plugin.

## Design

ColdFront provides an API to define additional user search classes for
extending the default search functionality. This app implements a
LDAPUserSearch class in utils.py which performs the LDAP search. This class is
then registered with ColdFront by setting "ADDITIONAL\_USER\_SEARCH\_CLASSES"
in local\_settings.py.

## Requirements

- pip install python-ldap ldap3

## Usage

To enable this plugin add the following in your `local_settings.py` file:

```
ADDITIONAL_USER_SEARCH_CLASSES = ['coldfront.plugins.ldap_user_search.utils.LDAPUserSearch',]
```
