import logging

from django.apps import AppConfig

from coldfront.core.utils.common import import_from_settings

ORGANIZATION_LDAP_AUTH_POPULATE_USER_ORGANIZATIONS = import_from_settings(
        'ORGANIZATION_LDAP_AUTH_POPULATE_USER_ORGANIZATIONS',
        False,
    )


logger = logging.getLogger(__name__)

class OrganizationConfig(AppConfig):
    name = 'coldfront.core.organization'
    verbose_name = 'Organization'

    def ready(self):
        # Only import signals if instructed to do so
        if ORGANIZATION_LDAP_AUTH_POPULATE_USER_ORGANIZATIONS:
            try:
                import coldfront.core.organization.signals
                import sys
            except Exception as error:
                logger.error("Not populating user organizations "
                        "from LDAP --- error importing organization."
                    "signals: {}".format(error))
        return
