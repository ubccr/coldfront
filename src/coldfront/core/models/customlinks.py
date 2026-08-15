# SPDX-FileCopyrightText: (C) DigitalOcean, LLC
# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

import urllib.parse

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from coldfront.core.choices import CustomLinkButtonClassChoices
from coldfront.models import ChangeLoggedModel
from coldfront.models.features import CloningMixin
from coldfront.utils.html import clean_html
from coldfront.utils.jinja2 import render_jinja2


class CustomLink(CloningMixin, ChangeLoggedModel):
    """
    A custom link to an external representation of a ColdFront object. The link
    text and URL fields accept Jinja2 template code to be rendered with an
    object as context.
    """

    object_types = models.ManyToManyField(
        to=ContentType,
        related_name="custom_links",
        help_text=_("The object type(s) to which this link applies."),
    )
    name = models.CharField(
        verbose_name=_("name"),
        max_length=100,
        unique=True,
    )
    enabled = models.BooleanField(
        verbose_name=_("enabled"),
        default=True,
    )
    link_text = models.TextField(
        verbose_name=_("link text"),
        help_text=_("Jinja2 template code for link text"),
    )
    link_url = models.TextField(
        verbose_name=_("link URL"),
        help_text=_("Jinja2 template code for link URL"),
    )
    weight = models.PositiveSmallIntegerField(
        verbose_name=_("weight"),
        default=100,
    )
    group_name = models.CharField(
        verbose_name=_("group name"),
        max_length=50,
        blank=True,
        help_text=_("Links with the same group will appear as a dropdown menu"),
    )
    button_class = models.CharField(
        verbose_name=_("button class"),
        max_length=30,
        choices=CustomLinkButtonClassChoices,
        default=CustomLinkButtonClassChoices.DEFAULT,
        help_text=_("The class of the first link in a group will be used for the dropdown button"),
    )
    new_window = models.BooleanField(
        verbose_name=_("new window"),
        default=False,
        help_text=_("Force link to open in a new window"),
    )

    clone_fields = (
        "object_types",
        "enabled",
        "weight",
        "group_name",
        "button_class",
        "new_window",
    )

    class Meta:
        ordering = ["group_name", "weight", "name"]
        indexes = (models.Index(fields=("group_name", "weight", "name")),)
        verbose_name = _("custom link")
        verbose_name_plural = _("custom links")

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("core:customlink", args=[self.pk])

    def render(self, context):
        """
        Render the CustomLink given the provided context, and return the text,
        link, and link_target.

        Args:
            context: The context passed to Jinja2

        Returns:
            dict with "text", "link", "link_target" keys, or empty dict if
            rendered text is empty.
        """
        text = render_jinja2(self.link_text, context).strip()
        if not text:
            return {}
        link = render_jinja2(self.link_url, context).strip()
        link_target = ' target="_blank"' if self.new_window else ""

        # Sanitize link text
        allowed_schemes = settings.ALLOWED_URL_SCHEMES
        # Sanitize link text
        allowed_schemes = getattr(settings, "ALLOWED_URL_SCHEMES", ["http", "https", "ftp", "mailto"])
        text = clean_html(text, allowed_schemes)

        # Sanitize link
        link = urllib.parse.quote(link, safe="/:?&=%+[]@#,;!")

        # Verify link scheme is allowed
        result = urllib.parse.urlparse(link)
        if result.scheme and result.scheme not in allowed_schemes:
            link = ""

        return {
            "text": text,
            "link": link,
            "link_target": link_target,
        }
