# SPDX-FileCopyrightText: (C) ColdFront Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

import json
import logging
import os

import ldap.filter
from django.core.exceptions import ImproperlyConfigured
from ldap3 import KERBEROS, SASL, Connection, Server

from coldfront.core.user.utils import UserSearch
from coldfront.core.utils.common import import_from_settings

logger = logging.getLogger(__name__)


class LDAPUserSearch(UserSearch):
    search_source = "LDAP"

    def __init__(self, user_search_string, search_by):
        super().__init__(user_search_string, search_by)
        self.FREEIPA_SERVER = import_from_settings("FREEIPA_SERVER")
        self.FREEIPA_USER_SEARCH_BASE = import_from_settings("FREEIPA_USER_SEARCH_BASE", "cn=users,cn=accounts")
        self.FREEIPA_KTNAME = import_from_settings("FREEIPA_KTNAME", "")

        self.server = Server("ldap://{}".format(self.FREEIPA_SERVER), use_ssl=True, connect_timeout=1)
        if len(self.FREEIPA_KTNAME) > 0:
            logger.info("Kerberos bind enabled: %s", self.FREEIPA_KTNAME)
            # kerberos SASL/GSSAPI bind
            os.environ["KRB5_CLIENT_KTNAME"] = self.FREEIPA_KTNAME
            self.conn = Connection(self.server, authentication=SASL, sasl_mechanism=KERBEROS, auto_bind=True)
        else:
            # anonomous bind
            self.conn = Connection(self.server, auto_bind=True)

        if not self.conn.bind():
            raise ImproperlyConfigured("Failed to bind to LDAP server: {}".format(self.conn.result))
        else:
            logger.info("LDAP bind successful: %s", self.conn.extend.standard.who_am_i())

    def parse_ldap_entry(self, entry):
        entry_dict = json.loads(entry.entry_to_json()).get("attributes")

        user_dict = {
            "last_name": entry_dict.get("sn")[0] if entry_dict.get("sn") else "",
            "first_name": entry_dict.get("givenName")[0] if entry_dict.get("givenName") else "",
            "username": entry_dict.get("uid")[0] if entry_dict.get("uid") else "",
            "email": entry_dict.get("mail")[0] if entry_dict.get("mail") else "",
            "source": self.search_source,
        }

        return user_dict

    def search_a_user(self, user_search_string=None, search_by="all_fields"):
        os.environ["KRB5_CLIENT_KTNAME"] = self.FREEIPA_KTNAME

        size_limit = 50
        if user_search_string and search_by == "all_fields":
            filter = ldap.filter.filter_format(
                "(&(|(givenName=*%s*)(sn=*%s*)(uid=*%s*)(mail=*%s*))(|(nsaccountlock=FALSE)(!(nsaccountlock=*))))",
                [user_search_string] * 4,
            )
        elif user_search_string and search_by == "username_only":
            filter = ldap.filter.filter_format(
                "(&(uid=%s)(|(nsaccountlock=FALSE)(!(nsaccountlock=*))))", [user_search_string]
            )
            size_limit = 1
        else:
            filter = "(objectclass=person)"

        searchParameters = {
            "search_base": self.FREEIPA_USER_SEARCH_BASE,
            "search_filter": filter,
            "attributes": ["uid", "sn", "givenName", "mail"],
            "size_limit": size_limit,
        }
        self.conn.search(**searchParameters)
        users = []
        for idx, entry in enumerate(self.conn.entries, 1):
            user_dict = self.parse_ldap_entry(entry)
            users.append(user_dict)

        logger.info("LDAP user search for %s found %s results", user_search_string, len(users))
        return users
