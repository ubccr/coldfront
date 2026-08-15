# SPDX-FileCopyrightText: (C) DigitalOcean, LLC
# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

import logging
import random
import re
import string
from contextlib import contextmanager

from django.contrib.auth.models import Permission
from django.utils.text import slugify

from coldfront.core.models import Tag
from coldfront.users.models import User


def create_tags(*names):
    """
    Create and return a Tag instance for each name given.
    """
    tags = [Tag(name=name, slug=slugify(name)) for name in names]
    Tag.objects.bulk_create(tags)
    return tags


def post_data(data):
    """
    Take a dictionary of test data (suitable for comparison to an instance) and return a dict suitable for POSTing.
    """
    ret = {}

    for key, value in data.items():
        if value is None:
            ret[key] = ""
        elif type(value) in (list, tuple):
            if value and hasattr(value[0], "pk"):
                # Value is a list of instances
                ret[key] = [v.pk for v in value]
            else:
                ret[key] = value
        elif hasattr(value, "pk"):
            # Value is an instance
            ret[key] = value.pk
        else:
            ret[key] = str(value)

    return ret


@contextmanager
def disable_warnings(logger_name):
    """
    Temporarily suppress expected warning messages to keep the test output clean.
    """
    logger = logging.getLogger(logger_name)
    current_level = logger.level
    logger.setLevel(logging.ERROR)
    yield
    logger.setLevel(current_level)


def get_random_string(length, charset=None):
    """
    Return a random string of the given length.
    """
    characters = string.ascii_letters + string.digits  # a-z, A-Z, 0-9
    return "".join(random.choice(characters) for __ in range(length))


def extract_form_failures(content):
    """
    Given raw HTML content from an HTTP response, return a list of form errors.
    """
    FORM_ERROR_REGEX = r"<!-- FORM-ERROR (.*) -->"
    return re.findall(FORM_ERROR_REGEX, str(content))


def create_test_user(username="testuser", permissions=None):
    """
    Create a User with the given permissions.
    """
    user = User.objects.create_user(username=username)
    if permissions is None:
        permissions = ()
    for perm_name in permissions:
        app, codename = perm_name.split(".")
        perm = Permission.objects.get(content_type__app_label=app, codename=codename)
        user.user_permissions.add(perm)

    return user
