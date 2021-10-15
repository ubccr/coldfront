from django.dispatch import receiver
from django_auth_ldap.backend import populate_user
from django.contrib.auth.models import User
from django_auth_ldap.backend import LDAPBackend

from coldfront.core.utils.common import import_from_settings
from coldfront.core.organization.models import Organization

ORGANIZATION_LDAP_USER_ATTRIBUTE = import_from_settings(
    'ORGANIZATION_LDAP_USER_ATTRIBUTE', [])
ORGANIZATION_LDAP_USER_ADD_PARENTS = import_from_settings(
    'ORGANIZATION_LDAP_USER_ADD_PARENTS', True)
ORGANIZATION_LDAP_USER_CREATE_PLACEHOLDERS = import_from_settings(
    'ORGANIZATION_LDAP_USER_CREATE_PLACEHOLDERS', True)
ORGANIZATION_LDAP_USER_DELETE_MISSING = import_from_settings(
    'ORGANIZATION_LDAP_USER_DELETE_MISSING', True)

@receiver(populate_user, sender=LDAPBackend)
def populate_user_organizations(sender, user, ldap_user,  **kwargs):
    # Save user object
    user.save()
    userProfile=user.userprofile
    dirstrings = ldap_user.attrs.get(
        ORGANIZATION_LDAP_USER_ATTRIBUTE, [])
    Organization.update_user_organizations_from_dirstrings(
        user=userProfile, 
        dirstrings=dirstrings, 
        addParents=ORGANIZATION_LDAP_USER_ADD_PARENTS,
        createUndefined=ORGANIZATION_LDAP_USER_CREATE_PLACEHOLDERS,
        delete=ORGANIZATION_LDAP_USER_DELETE_MISSING,
    )
    


