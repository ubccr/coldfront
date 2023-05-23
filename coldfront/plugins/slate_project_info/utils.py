import logging
import json

import ldap.filter
from coldfront.core.utils.common import import_from_settings
from ldap3 import Connection, Server

logger = logging.getLogger(__name__)


def get_slate_project_info_from_ldap(username):
    server = Server(
        import_from_settings('LDAP_SLATE_PROJECT_SERVER_URI'), use_ssl=True, connect_timeout=1
    )
    conn = Connection(server)
    if not conn.bind():
        logger.error('LDAP Slate Project: Failed to bind to LDAP server: {}'.format(conn.result))
        return []
    
    searchParameters = {
        'search_base': import_from_settings('LDAP_SLATE_PROJECT_USER_SEARCH_BASE'),
        'search_filter': ldap.filter.filter_format("(memberUid=%s)", [username]),
        'attributes': ['cn', 'description']
    }
    conn.search(**searchParameters)
    results = []
    if conn.entries:
        for entry in conn.entries:
            results.append(json.loads(entry.entry_to_json()).get('attributes'))

        logger.info(f'Slate project info found for user {username}')
    else:
        logger.info(f'Slate project info not found for user {username}')
        return []

    return results
