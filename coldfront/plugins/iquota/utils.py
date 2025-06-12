# SPDX-FileCopyrightText: (C) ColdFront Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

import os

import humanize
import kerberos
import requests

from coldfront.core.utils.common import import_from_settings
from coldfront.plugins.iquota.exceptions import KerberosError, MissingQuotaError


class Iquota:
    def __init__(self, username, groups):
        """Initialize settings."""
        self.IQUOTA_API_HOST = import_from_settings("IQUOTA_API_HOST")
        self.IQUOTA_API_PORT = import_from_settings("IQUOTA_API_PORT")
        self.IQUOTA_CA_CERT = import_from_settings("IQUOTA_CA_CERT")
        self.IQUOTA_KEYTAB = import_from_settings("IQUOTA_KEYTAB")
        self.username = username
        self.groups = groups

    def gssclient_token(self):
        os.environ["KRB5_CLIENT_KTNAME"] = self.IQUOTA_KEYTAB

        service = "HTTP@" + self.IQUOTA_API_HOST

        try:
            (_, vc) = kerberos.authGSSClientInit(service)
            kerberos.authGSSClientStep(vc, "")
            return kerberos.authGSSClientResponse(vc)
        except kerberos.GSSError:
            raise KerberosError("error initializing GSS client")

    def _humanize_user_quota(self, path, user_used, user_limit):
        user_quota = {
            "path": path,
            "username": self.username,
            "used": humanize.naturalsize(user_used),
            "limit": humanize.naturalsize(user_limit),
            "percent_used": round((user_used / user_limit) * 100),
        }

        return user_quota

    def get_user_quota(self):
        token = self.gssclient_token()

        headers = {"Authorization": "Negotiate " + token}
        url = "https://{}:{}/quota?user={}".format(self.IQUOTA_API_HOST, self.IQUOTA_API_PORT, self.username)

        r = requests.get(url, headers=headers, verify=self.IQUOTA_CA_CERT)

        try:
            usage = r.json()[0]
        except KeyError:
            raise MissingQuotaError("Missing user quota for username: %s" % (self.username))
        else:
            user_used = usage["used"]
            user_limit = usage["soft_limit"]
            return self._humanize_user_quota(usage["path"], user_used, user_limit)

    def _humanize_group_quota(self, path, group_user, group_limit):
        group_quota = {
            "path": path,
            "used": humanize.naturalsize(group_user),
            "limit": humanize.naturalsize(group_limit),
            "percent_used": round((group_user / group_limit) * 100),
        }

        return group_quota

    def _get_group_quota(self, group):
        token = self.gssclient_token()

        headers = {"Authorization": "Negotiate " + token}

        url = "https://{}:{}/quota?group={}".format(self.IQUOTA_API_HOST, self.IQUOTA_API_PORT, group)

        r = requests.get(url, headers=headers, verify=self.IQUOTA_CA_CERT)

        try:
            usage = r.json()
            usage[0]
        except Exception:
            return []

        quotas = []
        for q in usage:
            group_limit = q["soft_limit"]
            group_used = q["used"]

            if group_limit == 0:
                continue

            quotas.append(self._humanize_group_quota(q["path"], group_used, group_limit))

        return quotas

    def get_group_quotas(self):
        if not self.groups:
            return None

        group_quotas = {}
        for group in self.groups:
            group_quota = self._get_group_quota(group)
            for g in group_quota:
                group_quotas[g["path"]] = g

        return group_quotas
