# SPDX-FileCopyrightText: (C) DigitalOcean, LLC
# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from dataclasses import dataclass
from typing import Iterable

from django.db.models import QuerySet
from django.urls import reverse
from django.urls.exceptions import NoReverseMatch
from django.utils.translation import gettext_lazy as _

from coldfront.core.models import ObjectType
from coldfront.utils.request import safe_for_redirect
from coldfront.utils.strings import title

from .utils import get_action_url


class GetReturnURLMixin:
    """
    Provides logic for determining where a user should be redirected after processing a form.
    """

    default_return_url = None

    def get_return_url(self, request, obj=None):

        # First, see if `return_url` was specified as a query parameter or form data. Use this URL only if it's
        # considered safe.
        return_url = request.GET.get("return_url") or request.POST.get("return_url")
        if return_url and safe_for_redirect(return_url):
            return return_url

        # Next, check if the object being modified (if any) has an absolute URL.
        if obj is not None and obj.pk and hasattr(obj, "get_absolute_url"):
            return obj.get_absolute_url()

        # Fall back to the default URL (if specified) for the view.
        if self.default_return_url is not None:
            return reverse(self.default_return_url)

        # Attempt to dynamically resolve the list view for the object
        if hasattr(self, "queryset"):
            try:
                return get_action_url(self.queryset.model, action="list")
            except NoReverseMatch:
                pass

        # If all else fails, return home. Ideally this should never happen.
        return reverse("home")


class GetRelatedModelsMixin:
    """
    Provides logic for collecting all related models for the currently viewed model.
    """

    @dataclass
    class RelatedObjectCount:
        queryset: QuerySet
        filter_param: str
        label: str = ""

        @property
        def name(self):
            return self.label or title(_(self.queryset.model._meta.verbose_name_plural))

    def get_related_models(self, request, instance, omit=None, extra=None):
        """
        Get related models of the view's `queryset` model without those listed in `omit`. Will be sorted alphabetical.

        Args:
            request: Current request being processed.
            instance: The instance related models should be looked up for. A list of instances can be passed to match
                related objects in this list (e.g. to find sites of a region including child regions).
            omit: Remove relationships to these models from the result. Needs to be passed, if related models don't
                provide a `_list` view.
            extra: Add extra models to the list of automatically determined related models. Can be used to add indirect
                relationships.
        """
        omit = omit or []
        model = self.queryset.model
        related = filter(lambda m: m[0] is not model and m[0] not in omit, ObjectType.get_related_models(model, False))

        related_models = [
            self.RelatedObjectCount(
                model.objects.restrict(request.user, "view").filter(
                    **({f"{field}__in": instance} if isinstance(instance, Iterable) else {field: instance})
                ),
                f"{field}_id",
            )
            for model, field in related
        ]
        if extra is not None:
            related_models.extend([self.RelatedObjectCount(*attrs) for attrs in extra])

        return sorted(
            filter(lambda roc: roc.queryset.exists(), related_models),
            key=lambda roc: roc.name,
        )
