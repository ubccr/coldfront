# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from generic_notifications.types import register

from coldfront.core.notifications import ColdFrontNotification


@register
class InvoiceNotificationType(ColdFrontNotification):
    key = "billing_invoice_notification"
    name = "Invoices"
    description = "Invoice notifications"

    def get_subject(self, notification):
        if notification.subject:
            return notification.subject
        return "Invoice Notification"

    def get_text(self, notification):
        if notification.text:
            return notification.text
        return "You have a new invoice notification"
