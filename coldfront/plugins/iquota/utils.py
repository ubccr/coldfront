import os

import humanize
import requests

import kerberos
from coldfront.core.utils.common import import_from_settings
from coldfront.plugins.iquota.exceptions import KerberosError, MissingQuotaError


class Iquota:

    def __init__(self, username, groups):
        """Initialize settings."""
        self.IQUOTA_API_HOST = import_from_settings('IQUOTA_API_HOST')
        self.IQUOTA_API_PORT = import_from_settings('IQUOTA_API_PORT')
        self.IQUOTA_CA_CERT = import_from_settings('IQUOTA_CA_CERT')
        self.IQUOTA_USER_PATH = import_from_settings('IQUOTA_USER_PATH')
        self.IQUOTA_GROUP_PATH = import_from_settings('IQUOTA_GROUP_PATH')
        self.IQUOTA_KEYTAB = import_from_settings('IQUOTA_KEYTAB')
        self.username = username
        self.groups = groups

    def gssclient_token(self):
        os.environ['KRB5_CLIENT_KTNAME'] = self.IQUOTA_KEYTAB

        service = "HTTP@" + self.IQUOTA_API_HOST

        try:
            (_, vc) = kerberos.authGSSClientInit(service)
            kerberos.authGSSClientStep(vc, "")
            return kerberos.authGSSClientResponse(vc)
        except kerberos.GSSError as e:
            raise KerberosError('error initializing GSS client')

    def _humanize_user_quota(self, user_used, user_limit):

        user_quota = {
            'username': self.username,
            'used': humanize.naturalsize(user_used),
            'limit': humanize.naturalsize(user_limit),
            'percent_used': round((user_used / user_limit) * 100)
        }

        return user_quota

    def get_user_quota(self):

        token = self.gssclient_token()

        headers = {"Authorization": "Negotiate " + token}
        url = "https://{}:{}/quota/user?user={}&path={}".format(
            self.IQUOTA_API_HOST,
            self.IQUOTA_API_PORT,
            self.username,
            self.IQUOTA_USER_PATH)

        r = requests.get(url, headers=headers, verify=self.IQUOTA_CA_CERT)

        try:
            usage = r.json()['quotas'][0]
        except KeyError as e:
            raise MissingQuotaError(
                'Missing user quota for username: %s' % (self.username))
        else:
            user_used = usage['usage']['logical']
            user_limit = usage['thresholds']['soft']
            return self._humanize_user_quota(user_used, user_limit)

    def _humanize_group_quota(self, group_user, group_limit):

        group_quota = {
            'used': humanize.naturalsize(group_user),
            'limit': humanize.naturalsize(group_limit),
            'percent_used': round((group_user / group_limit) * 100)
        }

        return group_quota

    def _get_group_quota(self, group):

        token = self.gssclient_token()

        headers = {"Authorization": "Negotiate " + token}

        url = "https://{}:{}/quota/group?user={}&path={}&group={}".format(
            self.IQUOTA_API_HOST,
            self.IQUOTA_API_PORT,
            self.username,
            self.IQUOTA_GROUP_PATH,
            group)

        r = requests.get(url, headers=headers, verify=self.IQUOTA_CA_CERT)

        if 'code' in r.json() and r.json()['code'] == 'AEC_NOT_FOUND':
            return None
        try:
            usage = r.json()['quotas'][0]
        except:
            return None

        group_limit = usage['thresholds']['soft']

        if group_limit < 1000000:  # 1.0 MB
            return None

        group_used = usage['usage']['logical']

        return self._humanize_group_quota(group_used, group_limit)

    def get_group_quotas(self):

        if not self.groups:
            return None

        group_quotas = {}
        for group in self.groups:
            group_quota = self._get_group_quota(group)
            if group_quota:
                group_quotas[group] = group_quota

        return group_quotas
