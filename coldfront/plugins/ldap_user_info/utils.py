import logging
import json

import ldap.filter
from coldfront.core.utils.common import import_from_settings
from ldap3 import Connection, Server

logger = logging.getLogger(__name__)


def get_user_info(username, attributes):
    ldap_search = LDAPSearch()
    return ldap_search.search_a_user(
        username,
        attributes
    )


def check_if_user_exists(username):
    ldap_search = LDAPSearch()
    attributes = ldap_search.search_a_user(
        username,
        ['memberOf']
    )

    return not attributes['memberOf'][0] == ''


class LDAPSearch:
    search_source = 'LDAP'

    def __init__(self):
        self.LDAP_SERVER_URI = import_from_settings('LDAP_USER_SEARCH_SERVER_URI')
        self.LDAP_USER_SEARCH_BASE = import_from_settings('LDAP_USER_SEARCH_BASE')
        self.LDAP_BIND_DN = import_from_settings('LDAP_USER_SEARCH_BIND_DN', None)
        self.LDAP_BIND_PASSWORD = import_from_settings('LDAP_USER_SEARCH_BIND_PASSWORD', None)

        self.server = Server(self.LDAP_SERVER_URI, use_ssl=True, connect_timeout=1)
        self.conn = Connection(self.server, self.LDAP_BIND_DN, self.LDAP_BIND_PASSWORD, auto_bind=True)

        if not self.conn.bind():
            logger.error('LDAPSearch: Failed to bind to LDAP server: {}'.format(self.conn.result))
        else:
            logger.info('LDAPSearch: LDAP bind successful: %s', self.conn.extend.standard.who_am_i())

    def search_a_user(self, user_search_string=None, search_attributes_list=None):
        # Add check if debug is true to run this. If debug is not then write an error to log file.
        assert type(search_attributes_list) is list, 'search_attributes_list should be a list'

        if type(user_search_string) is not str:
            return dict.fromkeys(search_attributes_list, None)

        searchParameters = {'search_base': self.LDAP_USER_SEARCH_BASE,
                            'search_filter': ldap.filter.filter_format("(cn=%s)", [user_search_string]),
                            'attributes': search_attributes_list,
                            'size_limit': 1}
        self.conn.search(**searchParameters)
        attributes = {}
        if self.conn.entries:
            attributes = json.loads(self.conn.entries[0].entry_to_json()).get('attributes')
        else:
            attributes = dict.fromkeys(search_attributes_list, [''])

        return attributes
