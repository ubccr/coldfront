# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from dataclasses import dataclass, field
from typing import Any

from django.conf import settings
from djmoney.money import Money
from shortuuid import ShortUUID


def auto_generate_slug(model_instance=None):
    """Auto generate a slug. This is the default implementation which generates a shortuuid of length 7 form a numeric alphabet"""

    from coldfront.ras.models import Allocation, Project

    prefix = "cf"

    if model_instance is not None:
        if issubclass(model_instance.__class__, Project):
            prefix = "p"
        elif issubclass(model_instance.__class__, Allocation):
            prefix = "a"

    return prefix + ShortUUID(alphabet="0123456789").random(length=7)


def get_default_currency():
    """Default currency used for MoneyFields"""
    return settings.DEFAULT_CURRENCY


def get_currency_choices():
    """Default currency choices for MoneyFields"""
    return settings.DEFAULT_CURRENCY_CHOICES


def get_default_zero():
    return Money("0.00", settings.DEFAULT_CURRENCY)


def get_requestable_resources(user):
    from coldfront.core.models import ObjectType
    from coldfront.users.querysets import RestrictedQuerySet

    resources = []
    for ot in ObjectType.objects.with_feature("allocatable_resource").order_by("app_label", "model"):
        model_class = ot.model_class()
        if model_class is None:
            continue

        qs = model_class.objects.all()
        if issubclass(qs.__class__, RestrictedQuerySet):
            qs = qs.restrict(user, "view")

        for obj in qs:
            if obj.allocatable(user):
                resources.append(obj)

    return resources


@dataclass
class ResourceGroup:
    """
    A group of requestable resources
    """

    name: str
    link: str
    resources: list[Any] = field(default_factory=list)


def get_requestable_resources_by_group(user):
    from coldfront.views import get_action_url

    groups = {}
    for r in get_requestable_resources(user):
        group = groups.get(
            r._meta.verbose_name, ResourceGroup(link=get_action_url(r, "list"), name=r._meta.verbose_name)
        )
        group.resources.append(r)
        groups[r._meta.verbose_name] = group

    return [groups[k] for k in sorted(groups)]
