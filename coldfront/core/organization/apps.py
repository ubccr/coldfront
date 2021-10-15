import logging

from django.apps import AppConfig

from coldfront.core.utils.common import import_from_settings

ORGANIZATION_LDAP_AUTH_POPULATE_USER_ORGANIZATIONS=import_from_settings(
        'ORGANIZATION_LDAP_AUTH_POPULATE_USER_ORGANIZATIONS', False)
PLUGIN_AUTH_LDAP=import_from_settings(
        'PLUGIN_AUTH_LDAP', False)

logger = logging.getLogger(__name__)

class OrganizationConfig(AppConfig):
    name = 'coldfront.core.organization'
    verbose_name = 'Organization'

    def ready(self):
        # Only import signals if both PLUGIN_AUTH_LDAP and
        # ORGANIZATION_LDAP_AUTH_POPULATE_USER_ORGANIZATIONS set
        if ORGANIZATION_LDAP_AUTH_POPULATE_USER_ORGANIZATIONS \
                and PLUGIN_AUTH_LDAP:
                    try:
                        import coldfront.core.organization.signals
                    except Exception as error:
                        logger.error("Not populating user organizations "
                                "from LDAP --- error importing organization."
                                "signals: {}".format(error))
        return
