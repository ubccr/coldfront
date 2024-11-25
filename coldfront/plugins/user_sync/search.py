import json
import logging

from coldfront.core.utils.common import import_from_settings
from django.core.exceptions import ImproperlyConfigured
from ldap3 import Connection, Server

logger = logging.getLogger(__name__)

class LDAPUnixUIDSearch():

    def __init__(self):
        self.LDAP_SERVER = import_from_settings('LDAP_SERVER', '')
        self.LDAP_USER_SEARCH_BASE = import_from_settings('LDAP_USER_SEARCH_BASE', 'cn=users,cn=accounts')

        self.server = Server('ldap://{}'.format(self.LDAP_SERVER), use_ssl=True, connect_timeout=1)

    def get_connection(self):
        conn =  Connection(self.server, auto_bind=True)
        if not conn.bind():
            raise ImproperlyConfigured('Failed to bind to LDAP server: {}'.format(conn.result))
        else:
            logger.info('LDAP bind successful: %s', conn.extend.standard.who_am_i())
        return conn

    @staticmethod
    def parse_ldap_entry(entry):
        entry_dict = json.loads(entry.entry_to_json()).get('attributes')

        return {
            'last_name': entry_dict.get('sn', [None])[0],
            'first_name': entry_dict.get('givenName', [None])[0],
            'username': entry_dict.get('uid', [None])[0],
            'email': entry_dict.get('mail', None),
            'unix_uid': entry_dict.get('uidNumber', None),
            'affiliation': entry_dict.get('eduPersonAffiliation', [])
        }

    def get_info(self, username=None):
        searchParameters = {'search_base': self.LDAP_USER_SEARCH_BASE,
                            'search_filter': f'(uid={username})',
                            'attributes': ['uid', 'uidNumber', 'sn', 'givenName', 'mail', 'eduPersonAffiliation'],
                            'size_limit': 10}
        conn = self.get_connection()
        conn.search(**searchParameters)
        users = []
        for idx, entry in enumerate(conn.entries, 1):
            user_dict = LDAPUnixUIDSearch.parse_ldap_entry(entry)
            users.append(user_dict)

        if len(users) > 1:
            raise ValueError('Multiple users found for username: {}'.format(username))
        elif len(users) == 0:
            raise ValueError('No users found for username: {}'.format(username))
        
        logger.info("LDAP user search for %s found", username)
        return users[0]
