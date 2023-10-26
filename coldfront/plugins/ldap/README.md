An LDAP plugin for interacting with AD.

## Setup

Add the following variables to your .env:
- AUTH_LDAP_SERVER_URI
- AUTH_LDAP_BIND_DN
- AUTH_LDAP_BIND_PASSWORD
- AUTH_LDAP_USER_SEARCH_BASE
- AUTH_LDAP_GROUP_SEARCH_BASE

You may also add the following variables to your .env:
- AUTH_LDAP_USE_SSL (default will be False)

To enable testing with a test LDAP server, add:
- TEST_AUTH_LDAP_SERVER_URI
- TEST_AUTH_LDAP_BIND_DN
- TEST_AUTH_LDAP_BIND_PASSWORD
- TEST_AUTH_LDAP_USER_SEARCH_BASE
- TEST_AUTH_LDAP_GROUP_SEARCH_BASE
