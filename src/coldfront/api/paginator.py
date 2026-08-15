# SPDX-FileCopyrightText: (C) DigitalOcean, LLC
# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django.conf import settings
from django.db.models import QuerySet
from rest_framework.pagination import LimitOffsetPagination

from coldfront.api.exceptions import QuerySetNotOrdered


class OptionalLimitOffsetPagination(LimitOffsetPagination):
    """
    Override the stock paginator to allow setting limit=0 to disable pagination for a request. This returns all objects
    matching a query, but retains the same format as a paginated request. The limit can only be disabled if
    MAX_PAGE_SIZE has been set to 0 or None.
    """

    def __init__(self):
        self.default_limit = settings.PAGINATE_COUNT

    def paginate_queryset(self, queryset, request, view=None):

        if isinstance(queryset, QuerySet) and not queryset.ordered:
            raise QuerySetNotOrdered(
                "Paginating over an unordered queryset is unreliable. Ensure that a minimal "
                "ordering has been applied to the queryset for this API endpoint."
            )

        if isinstance(queryset, QuerySet):
            self.count = self.get_queryset_count(queryset)
        else:
            # We're dealing with an iterable, not a QuerySet
            self.count = len(queryset)

        self.limit = self.get_limit(request)
        self.offset = self.get_offset(request)
        self.request = request

        if self.limit and self.count > self.limit and self.template is not None:
            self.display_page_controls = True

        if self.count == 0 or self.offset > self.count:
            return list()

        if self.limit:
            return list(queryset[self.offset : self.offset + self.limit])
        return list(queryset[self.offset :])

    def get_limit(self, request):
        max_limit = self.default_limit
        MAX_PAGE_SIZE = settings.MAX_PAGE_SIZE
        if MAX_PAGE_SIZE:
            max_limit = min(max_limit, MAX_PAGE_SIZE)

        if self.limit_query_param:
            try:
                limit = int(request.query_params[self.limit_query_param])
                if limit < 0:
                    raise ValueError()

                if MAX_PAGE_SIZE:
                    if limit == 0:
                        max_limit = MAX_PAGE_SIZE
                    else:
                        max_limit = min(MAX_PAGE_SIZE, limit)
                else:
                    max_limit = limit
            except (KeyError, ValueError):
                pass

        return max_limit

    def get_queryset_count(self, queryset):
        return queryset.count()

    def get_next_link(self):

        # Pagination has been disabled
        if not self.limit:
            return None

        return super().get_next_link()

    def get_previous_link(self):

        # Pagination has been disabled
        if not self.limit:
            return None

        return super().get_previous_link()
