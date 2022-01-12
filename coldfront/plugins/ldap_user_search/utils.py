import json
import logging

import ldap.filter
from coldfront.core.user.utils import UserSearch
from coldfront.core.utils.common import import_from_settings
from ldap3 import Connection, Server

logger = logging.getLogger(__name__)

class LDAPUserSearch(UserSearch):
    search_source = 'LDAP'

    def __init__(self, user_search_string, search_by):
        super().__init__(user_search_string, search_by)
        self.LDAP_SERVER_URI = import_from_settings('LDAP_USER_SEARCH_SERVER_URI')
        self.LDAP_USER_SEARCH_BASE = import_from_settings('LDAP_USER_SEARCH_BASE')
        self.LDAP_BIND_DN = import_from_settings('LDAP_USER_SEARCH_BIND_DN', None)
        self.LDAP_BIND_PASSWORD = import_from_settings('LDAP_USER_SEARCH_BIND_PASSWORD', None)
        self.LDAP_CONNECT_TIMEOUT = import_from_settings('LDAP_USER_SEARCH_CONNECT_TIMEOUT', 2.5)
        self.LDAP_USE_SSL = import_from_settings('LDAP_USER_SEARCH_USE_SSL', True)

        self.server = Server(self.LDAP_SERVER_URI, use_ssl=self.LDAP_USE_SSL, connect_timeout=self.LDAP_CONNECT_TIMEOUT)
        self.conn = Connection(self.server, self.LDAP_BIND_DN, self.LDAP_BIND_PASSWORD, auto_bind=True)

    def parse_ldap_entry(self, entry):
        entry_dict = json.loads(entry.entry_to_json()).get('attributes')

        user_dict = {
            'last_name': entry_dict.get('sn')[0] if entry_dict.get('sn') else '',
            'first_name': entry_dict.get('givenName')[0] if entry_dict.get('givenName') else '',
            'username': entry_dict.get('uid')[0] if entry_dict.get('uid') else '',
            'email': entry_dict.get('mail')[0] if entry_dict.get('mail') else '',
            'source': self.search_source,
        }

        return user_dict

    def search_a_user(self, user_search_string=None, search_by='all_fields'):
        size_limit = 50
        if user_search_string and search_by == 'all_fields':
            filter = ldap.filter.filter_format("(|(givenName=*%s*)(sn=*%s*)(uid=*%s*)(mail=*%s*))", [user_search_string] * 4)
        elif user_search_string and search_by == 'username_only':
            filter = ldap.filter.filter_format("(uid=%s)", [user_search_string])
            size_limit = 1
        else:
            filter = '(objectclass=person)'

        searchParameters = {'search_base': self.LDAP_USER_SEARCH_BASE,
                            'search_filter': filter,
                            'attributes': ['uid', 'sn', 'givenName', 'mail'],
                            'size_limit': size_limit}
        self.conn.search(**searchParameters)
        users = []
        for idx, entry in enumerate(self.conn.entries, 1):
            user_dict = self.parse_ldap_entry(entry)
            users.append(user_dict)

        logger.info("LDAP user search for %s found %s results", user_search_string, len(users))
        return users
