# SPDX-FileCopyrightText: (C) DigitalOcean, LLC
# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

import decimal
import json

from django import template
from django.core.serializers.json import DjangoJSONEncoder
from django.urls import NoReverseMatch
from django.utils.html import conditional_escape
from taggit.managers import _TaggableManager

from coldfront.views import get_action_url


class JobLogDecoder(json.JSONDecoder):
    """Custom JSON decoder for Job log entries."""

    pass


class CustomFieldJSONEncoder(DjangoJSONEncoder):
    """
    Override Django's built-in JSON encoder to save decimal values as JSON numbers.
    """

    def default(self, o):
        if isinstance(o, decimal.Decimal):
            return float(o)
        return super().default(o)


def is_taggable(obj):
    """
    Return True if the instance can have Tags assigned to it; False otherwise.
    """
    if hasattr(obj, "tags"):
        if issubclass(obj.tags.__class__, _TaggableManager):
            return True
    return False


class ActionURLNode(template.Node):
    """Template node for the {% action_url %} template tag."""

    child_nodelists = ()

    def __init__(self, model, action, kwargs, asvar=None):
        self.model = model
        self.action = action
        self.kwargs = kwargs
        self.asvar = asvar

    def __repr__(self):
        return (
            f"<{self.__class__.__qualname__} "
            f"model='{self.model}' "
            f"action='{self.action}' "
            f"kwargs={repr(self.kwargs)} "
            f"as={repr(self.asvar)}>"
        )

    def render(self, context):
        """
        Render the action URL node.

        Args:
            context: The template context

        Returns:
            The resolved URL or empty string if using 'as' syntax

        Raises:
            NoReverseMatch: If the URL cannot be resolved and not using 'as' syntax
        """
        # Resolve model and kwargs from context
        model = self.model.resolve(context)
        kwargs = {k: v.resolve(context) for k, v in self.kwargs.items()}

        # Get the action URL using the utility function
        try:
            url = get_action_url(model, action=self.action, kwargs=kwargs)
        except NoReverseMatch:
            if self.asvar is None:
                raise
            url = ""

        # Handle variable assignment or return escaped URL
        if self.asvar:
            context[self.asvar] = url
            return ""

        return conditional_escape(url) if context.autoescape else url
