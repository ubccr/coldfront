import json

from django.db.models import Q
from ldap3 import Connection, Server

from common.djangoapps.user.utils import UserSearch
from common.djangolibs.utils import import_from_settings


class LDAPUserSearch(UserSearch):
    search_source = 'LDAP'

    def __init__(self, user_search_string, search_by):
        super().__init__(user_search_string, search_by)
        self.AUTH_LDAP_SERVER_URI = import_from_settings('AUTH_LDAP_SERVER_URI')
        self.AUTH_LDAP_USER_SEARCH_BASE = import_from_settings('AUTH_LDAP_USER_SEARCH_BASE')
        self.AUTH_LDAP_BIND_DN = import_from_settings('AUTH_LDAP_BIND_DN', None)
        self.AUTH_LDAP_BIND_PASSWORD = import_from_settings('AUTH_LDAP_BIND_PASSWORD', None)

        self.server = Server(self.AUTH_LDAP_SERVER_URI, use_ssl=True, connect_timeout=1)
        self.conn = Connection(self.server, self.AUTH_LDAP_BIND_DN, self.AUTH_LDAP_BIND_PASSWORD, auto_bind=True)

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
            filter = "(|(givenName=*{}*)(sn=*{}*)(uid=*{}*)(mail=*{}*))".format(*[user_search_string] * 4)
        elif user_search_string and search_by == 'username_only':
            filter = "(uid={})".format(user_search_string)
            size_limit = 1
        else:
            filter = '(objectclass=person)'

        searchParameters = {'search_base': self.AUTH_LDAP_USER_SEARCH_BASE,
                            'search_filter': filter,
                            'attributes': ['uid', 'sn', 'givenName', 'mail'],
                            'size_limit': size_limit}
        self.conn.search(**searchParameters)
        users = []
        for idx, entry in enumerate(self.conn.entries, 1):
            user_dict = self.parse_ldap_entry(entry)
            users.append(user_dict)

        return users
