# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

import django_filters
from django.db.models import Q
from django.utils.translation import gettext as _
from generic_notifications.models import Notification
from generic_notifications.utils import get_notifications

from coldfront.views.filtersets import BaseFilterSet


class NotificationFilterSet(BaseFilterSet):
    q = django_filters.CharFilter(
        method="search",
        label=_("Search"),
    )

    class Meta:
        model = Notification
        fields = ("subject", "text")

    def search(self, queryset, name, value):
        user = getattr(self.request, "user", None)
        if not user:
            return Notification.objects.none()

        if not value.strip():
            return get_notifications(user=user)
        return get_notifications(user=user).filter(Q(subject__icontains=value) | Q(text__icontains=value))
