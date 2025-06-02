# SPDX-FileCopyrightText: (C) ColdFront Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
import os

from django.core.exceptions import ImproperlyConfigured
from ipalib import api

from coldfront.core.utils.common import import_from_settings

CLIENT_KTNAME = import_from_settings("FREEIPA_KTNAME")
UNIX_GROUP_ATTRIBUTE_NAME = import_from_settings("FREEIPA_GROUP_ATTRIBUTE_NAME", "freeipa_group")
FREEIPA_NOOP = import_from_settings("FREEIPA_NOOP", False)

logger = logging.getLogger(__name__)


class ApiError(Exception):
    pass


class AlreadyMemberError(ApiError):
    pass


class NotMemberError(ApiError):
    pass


try:
    os.environ["KRB5_CLIENT_KTNAME"] = CLIENT_KTNAME
    api.bootstrap()
    api.finalize()
    api.Backend.rpcclient.connect()
except Exception as e:
    logger.error("Failed to initialze FreeIPA lib: %s", e)
    raise ImproperlyConfigured("Failed to initialze FreeIPA: {0}".format(e))


def check_ipa_group_error(res):
    if not res:
        raise ValueError("Missing FreeIPA response")

    if res["completed"] == 1:
        return

    res["failed"]["member"]["user"][0][0]
    res["result"]["cn"][0]
    err_msg = res["failed"]["member"]["user"][0][1]

    # Check if user is already a member
    if err_msg == "This entry is already a member":
        raise AlreadyMemberError(err_msg)

    # Check if user is not a member
    if err_msg == "This entry is not a member":
        raise NotMemberError(err_msg)

    raise ApiError(err_msg)
