# SPDX-FileCopyrightText: (C) DigitalOcean, LLC
# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from crispy_forms.layout import Layout
from django import forms
from django.utils.translation import gettext_lazy as _
from generic_notifications.registry import registry

from coldfront.forms.fields.dynamic import DynamicModelMultipleChoiceField
from coldfront.forms.mixins import HorizontalFormMixin
from coldfront.users.models import Group, User


class RenderMarkdownForm(forms.Form):
    """
    Provides basic validation for markup to be rendered.
    """

    text = forms.CharField(label=_("Text"), required=False)


class AdminNotificationForm(HorizontalFormMixin, forms.Form):
    """
    Form for superusers to send notifications to users.
    """

    notify_all = forms.BooleanField(
        label=_("Notify all users"),
        required=False,
        help_text=_("Send this notification to every registered user."),
    )
    users = DynamicModelMultipleChoiceField(
        label=_("Users"),
        required=False,
        queryset=User.objects.all(),
    )
    groups = DynamicModelMultipleChoiceField(
        label=_("Groups"),
        required=False,
        queryset=Group.objects.all(),
    )
    notification_type = forms.ChoiceField(
        label=_("Notification type"),
        choices=[],
        required=True,
    )
    subject = forms.CharField(
        label=_("Subject"),
        max_length=255,
        required=True,
    )
    text = forms.CharField(
        label=_("Message"),
        widget=forms.Textarea,
        required=True,
    )

    fieldsets = (
        Layout(
            "notify_all",
            "users",
            "groups",
            "notification_type",
            "subject",
            "text",
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Populate notification type choices from the registry
        type_choices = []
        for nt in registry.get_all_types():
            type_choices.append((nt.key, nt.name))
        self.fields["notification_type"].choices = type_choices
