import logging
import json

import ldap.filter
from ldap3 import Connection, Server
from coldfront.core.utils.common import import_from_settings

logger = logging.getLogger(__name__)


def get_user_info(username, attributes, ldap_search=None):
    if ldap_search is None:
        ldap_search = LDAPSearch()

    return ldap_search.search_a_user(username, attributes)


def get_users_info(usernames, attributes):
    ldap_search = LDAPSearch()
    results = {}
    for username in usernames:
        results[username] = get_user_info(username, attributes, ldap_search)

    return results


def check_if_user_exists(username, ldap_search=None):
    attributes = get_user_info(username, ['memberOf'], ldap_search)
    return not attributes['memberOf'][0] == ''


def check_if_users_exist(usernames):
    ldap_search = LDAPSearch()
    not_found_users = []
    found_users = []
    for username in usernames:
        if check_if_user_exists(username, ldap_search):
            found_users.append(username)
        else:
            not_found_users.append(username)

    return found_users, not_found_users


class LDAPSearch:
    search_source = 'LDAP'

    def __init__(self):
        self.LDAP_SERVER_URI = import_from_settings('LDAP_USER_SEARCH_SERVER_URI')
        self.LDAP_USER_SEARCH_BASE = import_from_settings('LDAP_USER_SEARCH_BASE')
        self.LDAP_BIND_DN = import_from_settings('LDAP_USER_SEARCH_BIND_DN', None)
        self.LDAP_BIND_PASSWORD = import_from_settings('LDAP_USER_SEARCH_BIND_PASSWORD', None)
        self.LDAP_CONNECT_TIMEOUT = import_from_settings('LDAP_USER_SEARCH_CONNECT_TIMEOUT', 2.5)

        self.server = Server(self.LDAP_SERVER_URI, use_ssl=True, connect_timeout=self.LDAP_CONNECT_TIMEOUT)
        self.conn = Connection(self.server, self.LDAP_BIND_DN, self.LDAP_BIND_PASSWORD, auto_bind=True)

        if not self.conn.bind():
            logger.error('LDAPSearch: Failed to bind to LDAP server: {}'.format(self.conn.result))

    def search_a_user(self, user_search_string=None, search_attributes_list=None):
        # Add check if debug is true to run this. If debug is not then write an error to log file.
        assert type(search_attributes_list) is list, 'search_attributes_list should be a list'

        if type(user_search_string) is not str:
            return dict.fromkeys(search_attributes_list, None)

        searchParameters = {'search_base': self.LDAP_USER_SEARCH_BASE,
                            'search_filter': ldap.filter.filter_format("(sAMAccountName=%s)", [user_search_string]),
                            'attributes': search_attributes_list,
                            'size_limit': 1}
        self.conn.search(**searchParameters)
        attributes = {}
        if self.conn.entries:
            attributes = json.loads(self.conn.entries[0].entry_to_json()).get('attributes')
        else:
            attributes = dict.fromkeys(search_attributes_list, [''])

        return attributes
