# SPDX-FileCopyrightText: (C) DigitalOcean, LLC
# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

import logging
from urllib.parse import parse_qs, urlencode, urlparse

from django.conf import settings
from django.contrib import auth
from django.contrib.auth.middleware import RemoteUserMiddleware as RemoteUserMiddleware_
from django.core.exceptions import ImproperlyConfigured


class RemoteUserMiddleware(RemoteUserMiddleware_):
    """
    Custom implementation of Django's RemoteUserMiddleware which allows for a user-configurable HTTP header name.
    """

    async_capable = False
    force_logout_if_no_header = False

    def __init__(self, get_response):
        if get_response is None:
            raise ValueError("get_response must be provided.")
        self.get_response = get_response

    @property
    def header(self):
        return settings.REMOTE_AUTH_HEADER

    def __call__(self, request):
        logger = logging.getLogger("coldfront.auth.RemoteUserMiddleware")
        # Bypass middleware if remote authentication is not enabled
        if not settings.REMOTE_AUTH_ENABLED:
            return self.get_response(request)
        # AuthenticationMiddleware is required so that request.user exists.
        if not hasattr(request, "user"):
            raise ImproperlyConfigured(
                "The Django remote user auth middleware requires the"
                " authentication middleware to be installed.  Edit your"
                " MIDDLEWARE setting to insert"
                " 'django.contrib.auth.middleware.AuthenticationMiddleware'"
                " before the RemoteUserMiddleware class."
            )
        try:
            username = request.META[self.header]
        except KeyError:
            # If specified header doesn't exist then remove any existing
            # authenticated remote-user, or return (leaving request.user set to
            # AnonymousUser by the AuthenticationMiddleware).
            if self.force_logout_if_no_header and request.user.is_authenticated:
                self._remove_invalid_user(request)
            return self.get_response(request)
        # If the user is already authenticated and that user is the user we are
        # getting passed in the headers, then the correct user is already
        # persisted in the session and we don't need to continue.
        if request.user.is_authenticated:
            if request.user.get_username() == self.clean_username(username, request):
                return self.get_response(request)
            # An authenticated user is associated with the request, but
            # it does not match the authorized user in the header.
            self._remove_invalid_user(request)

        # We are seeing this user for the first time in this session, attempt
        # to authenticate the user.
        if settings.REMOTE_AUTH_GROUP_SYNC_ENABLED:
            logger.debug("Trying to sync Groups")
            user = auth.authenticate(request, remote_user=username, remote_groups=self._get_groups(request))
        else:
            user = auth.authenticate(request, remote_user=username)
        if user:
            # User is valid.
            # Update the User's Profile if set by request headers
            if settings.REMOTE_AUTH_USER_FIRST_NAME in request.META:
                user.first_name = request.META[settings.REMOTE_AUTH_USER_FIRST_NAME]
            if settings.REMOTE_AUTH_USER_LAST_NAME in request.META:
                user.last_name = request.META[settings.REMOTE_AUTH_USER_LAST_NAME]
            if settings.REMOTE_AUTH_USER_EMAIL in request.META:
                user.email = request.META[settings.REMOTE_AUTH_USER_EMAIL]
            user.save()

            # Set request.user and persist user in the session
            # by logging the user in.
            request.user = user
            auth.login(request, user)

        return self.get_response(request)

    def _get_groups(self, request):
        logger = logging.getLogger("coldfront.authentication.RemoteUserMiddleware")

        groups_string = request.META.get(settings.REMOTE_AUTH_GROUP_HEADER, None)
        if groups_string:
            groups = groups_string.split(settings.REMOTE_AUTH_GROUP_SEPARATOR)
        else:
            groups = []
        logger.debug(f"Groups are {groups}")
        return groups


class HtmxAuthRedirectMiddleware:
    """
    Middleware to handle HTMX authentication redirects properly.

    When an HTMX request results in a 302 redirect (typically for authentication),
    this middleware:
    1. Changes the response status code to 204 (No Content)
    2. Adds an HX-Redirect header with the redirect URL
    3. Preserves the original request path in the 'next' query parameter

    This ensures that after authentication, the user is returned to the page
    they were attempting to access, maintaining a seamless UX with HTMX.

    Credits: https://www.caktusgroup.com/blog/2022/11/11/how-handle-django-login-redirects-htmx/
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        # HTMX request returning 302 likely is login required.
        # Take the redirect location and send it as the HX-Redirect header value,
        # with 'next' query param set to where the request originated. Also change
        # response status code to 204 (no content) so that htmx will obey the
        # HX-Redirect header value.
        if request.headers.get("HX-Request") == "true" and response.status_code == 302:
            # Determine the next path from referer or current request path
            ref_header = request.headers.get("Referer", "")
            if ref_header:
                referer = urlparse(ref_header)
                next_path = referer.path
            else:
                next_path = request.path

            # Parse the redirect URL
            redirect_url = urlparse(response["location"])

            # Set response status code to 204 for HTMX to process the redirect
            response.status_code = 204

            # Update the "?next" query parameter
            query_params = parse_qs(redirect_url.query)
            query_params["next"] = [next_path]
            new_query = urlencode(query_params, doseq=True)

            # Set the new HX-Redirect header
            response.headers["HX-Redirect"] = f"{redirect_url.path}?{new_query}"

        return response
