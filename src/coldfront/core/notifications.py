# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from generic_notifications import send_notification
from generic_notifications.channels import WebsiteChannel
from generic_notifications.frequencies import RealtimeFrequency
from generic_notifications.types import NotificationType, register

logger = logging.getLogger(__name__)


class ColdFrontNotification(NotificationType):
    default_frequency = RealtimeFrequency
    default_channels = [WebsiteChannel]


@register
class SystemMessage(ColdFrontNotification):
    key = "system_message"
    name = "System Message"
    description = "Important system notifications"

    def get_subject(self, notification):
        """Generate subject for system messages."""
        if notification.subject:
            return notification.subject
        return f"System Message: {self.name}"

    def get_text(self, notification):
        """Generate text for system messages."""
        if notification.text:
            return notification.text
        return self.description or f"You have a new {self.name.lower()} notification"


def send_system_notification(*, target, subject, text, url=None):
    """
    Send a system notification to all configured admin recipients.

    Recipients are determined from settings:
    - All superusers (always included)
    - Additional users listed in SYSTEM_NOTIFICATION_USERS (by username)
    - All members of groups listed in SYSTEM_NOTIFICATION_GROUPS (by group name)

    Args:
        target: The object the notification is about
        subject: Notification subject line
        text: Notification body text
        url: Optional URL to link from the notification
    """
    User = get_user_model()
    recipients = set()

    # Always include superusers
    for user in User.objects.filter(is_superuser=True):
        recipients.add(user.pk)

    # Include additional users by username
    usernames = getattr(settings, "SYSTEM_NOTIFICATION_USERS", [])
    if usernames:
        for user in User.objects.filter(username__in=usernames):
            recipients.add(user.pk)

    # Include all members of additional groups
    group_names = getattr(settings, "SYSTEM_NOTIFICATION_GROUPS", [])
    if group_names:
        # Use the custom ColdFront Group model
        from coldfront.users.models import Group

        for group in Group.objects.filter(name__in=group_names):
            for user in group.users.all():
                recipients.add(user.pk)

    # Send notification to each unique recipient
    for user in User.objects.filter(pk__in=recipients):
        try:
            send_notification(
                recipient=user,
                notification_type=SystemMessage,
                target=target,
                subject=subject,
                text=text,
                url=url,
            )
        except Exception:
            logger.exception(
                "Failed to send system notification to user %s",
                user,
            )
