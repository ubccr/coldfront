# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from generic_notifications.types import register

from coldfront.core.notifications import ColdFrontNotification


@register
class AllocationsNotificationType(ColdFrontNotification):
    key = "allocations_notification"
    name = "Allocations"
    description = "Allocation notifications"

    def get_subject(self, notification):
        if notification.subject:
            return notification.subject
        return "Allocation Notification"

    def get_text(self, notification):
        if notification.text:
            return notification.text
        return "You have a new allocation notification"
