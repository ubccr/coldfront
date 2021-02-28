from coldfront.config.env import ENV
from coldfront.config.base import INSTALLED_APPS, TEMPLATES, DEVELOP

#------------------------------------------------------------------------------
# ColdFront authentication configs
#------------------------------------------------------------------------------
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
]

LOGIN_URL = '/user/login'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'

SU_LOGIN_CALLBACK = "coldfront.core.utils.common.su_login_callback"
SU_LOGOUT_REDIRECT_URL = "/admin/auth/user/"

SESSION_COOKIE_AGE = 60 * 15
SESSION_SAVE_EVERY_REQUEST = True
SESSION_COOKIE_SAMESITE  = 'Strict'
SESSION_COOKIE_SECURE = True

#------------------------------------------------------------------------------
# Enable administrators to login as other users
#------------------------------------------------------------------------------
if ENV.bool('ENABLE_SU', default=True):
    AUTHENTICATION_BACKENDS += ['django_su.backends.SuBackend',]
    INSTALLED_APPS.insert(0, 'django_su')
    TEMPLATES[0]['OPTIONS']['context_processors'].extend(['django_su.context_processors.is_su', ])

#------------------------------------------------------------------------------
# Example config for enabling LDAP user authentication using django-auth-ldap.
# This will enable LDAP user/password logins. Set this in local_settings.py
#------------------------------------------------------------------------------
# import ldap
# from django_auth_ldap.config import GroupOfNamesType, LDAPSearch
# from coldfront.config.base import AUTHENTICATION_BACKENDS
#
# AUTH_LDAP_SERVER_URI = 'ldap://localhost'
# AUTH_LDAP_USER_SEARCH_BASE = 'cn=users,cn=accounts,dc=localhost,dc=localdomain'
# AUTH_LDAP_START_TLS = True
# AUTH_LDAP_BIND_AS_AUTHENTICATING_USER=True
# AUTH_LDAP_MIRROR_GROUPS = True
# AUTH_LDAP_USER_SEARCH = LDAPSearch(
#     AUTH_LDAP_USER_SEARCH_BASE, ldap.SCOPE_ONELEVEL, '(uid=%(user)s)')
# AUTH_LDAP_GROUP_SEARCH_BASE = 'cn=groups,cn=accounts,dc=localhost,dc=localdomain'
# AUTH_LDAP_GROUP_SEARCH = LDAPSearch(
#     AUTH_LDAP_GROUP_SEARCH_BASE, ldap.SCOPE_ONELEVEL, '(objectClass=groupOfNames)')
# AUTH_LDAP_GROUP_TYPE = GroupOfNamesType()
# AUTH_LDAP_USER_ATTR_MAP = {
#     'username': 'uid',
#     'first_name': 'givenName',
#     'last_name': 'sn',
#     'email': 'mail',
# }
#
# AUTHENTICATION_BACKENDS += ['django_auth_ldap.backend.LDAPBackend',]
