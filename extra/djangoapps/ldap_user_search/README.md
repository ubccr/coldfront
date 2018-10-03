# LDAP user search for Coldfront

Coldfront django extra app providing user searching using LDAP. When adding
users to a subscription or a project, Coldfront will by default look in the
local database only. This app enables searching an LDAP directory.

## Design

Coldfront provides an API to define additional user search classes for
extending the default search functionality. This app implements a
LDAPUserSearch class in utils.py which performs the LDAP search. This class is
then registered with Coldfront by setting "ADDITIONAL\_USER\_SEARCH\_CLASSES"
in local\_settings.py.

## Requirements

- pip install python-ldap ldap3

## Usage

To enable this extra app add or uncomment the following in your
local\_settings.py file:

```
    ADDITIONAL_USER_SEARCH_CLASSES = ['extra.djangoapps.ldap_user_search.utils.LDAPUserSearch',]
```
