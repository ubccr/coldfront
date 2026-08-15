# SPDX-FileCopyrightText: (C) DigitalOcean, LLC
# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0


from collections import defaultdict
from contextlib import contextmanager

from django.conf import settings as django_settings
from generic_notifications.utils import get_unread_count

from coldfront.context import current_request, query_cache, signals_received
from coldfront.registry import register_request_processor
from coldfront.registry import registry as registry_

__all__ = (
    "registry",
    "settings",
    "unread_notifications_count",
)


@register_request_processor
@contextmanager
def event_tracking(request):
    """
    Queue interesting events in memory while processing a request, then flush that queue for processing by the
    events pipline before returning the response.

    :param request: WSGIRequest object with a unique `id` set
    """
    current_request.set(request)
    query_cache.set(defaultdict(dict))
    signals_received.set(defaultdict(dict))

    yield

    # Clear context vars
    current_request.set(None)
    query_cache.set(None)
    signals_received.set(None)


def registry(request):
    """
    Adds ColdFront registry items to the template context. Example: {{ registry.models.core }}
    """
    return {
        "registry": registry_,
    }


def settings(request):
    """
    Adds Django settings to the template context. Example: {{ settings.DEBUG }}
    """
    return {
        "settings": django_settings,
    }


def unread_notifications_count(request):
    """
    Adds the unread notifications count for the current user to the template context.
    """
    count = 0
    if request.user.is_authenticated:
        count = get_unread_count(request.user)
    return {
        "unread_notifications_count": count,
    }
