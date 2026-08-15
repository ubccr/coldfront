# SPDX-FileCopyrightText: (C) DigitalOcean, LLC
# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django.utils.http import url_has_allowed_host_and_scheme


def safe_for_redirect(url):
    """
    Returns True if the given URL is safe to use as an HTTP redirect; otherwise returns False.
    """
    return url_has_allowed_host_and_scheme(url, allowed_hosts=None)
