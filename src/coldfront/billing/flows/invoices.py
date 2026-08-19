# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django.db import transaction
from django.utils.translation import gettext_lazy as _
from generic_notifications import send_notification
from viewflow import fsm, this

from coldfront.billing import object_actions as actions
from coldfront.billing.choices import InvoiceStatusChoices
from coldfront.billing.generation import finalize_invoice, generate_invoice
from coldfront.billing.models import Invoice
from coldfront.billing.notifications import InvoiceNotificationType
from coldfront.flows import ColdFrontFlow
from coldfront.users.permissions import get_permission_for_model


class InvoiceStatusFlow(ColdFrontFlow):
    """
    Invoice Status workflow defines the transitions between the statuses of an
    Invoice: draft -> invoiced -> paid, with void from draft or invoiced.
    """

    status = fsm.State(InvoiceStatusChoices, default=InvoiceStatusChoices.STATUS_DRAFT)
    label = "Invoice"
    actions = (
        actions.GenerateObject,
        actions.InvoiceObject,
        actions.PayObject,
        actions.VoidObject,
    )

    def __init__(self, invoice):
        self.invoice = invoice

    @status.setter()
    def _set_invoice_status(self, value):
        self.invoice.status = value

    @status.getter()
    def _get_invoice_status(self):
        return self.invoice.status

    @status.on_success()
    def _on_success_transition(self, descriptor, source, target):
        if self.invoice is None:
            return

        with transaction.atomic():
            self.invoice.save()

        # Notify the owner on the meaningful transitions
        if target in {
            InvoiceStatusChoices.STATUS_INVOICED,
            InvoiceStatusChoices.STATUS_PAID,
            InvoiceStatusChoices.STATUS_VOID,
        }:
            invoice = self.invoice
            subject = f"Invoice {invoice.slug} {target}"
            text = _("Invoice '%(slug)s' is now %(status)s.") % {
                "slug": invoice.slug,
                "status": invoice.get_status_display(),
            }
            url = invoice.get_absolute_url()
            send_notification(
                recipient=invoice.owner,
                notification_type=InvoiceNotificationType,
                target=invoice,
                subject=subject,
                text=text,
                url=url,
            )

        # Dispatch registered plugin callbacks for this target state
        self._dispatch_target_callbacks(self.invoice, source=source, target=target)

    @status.transition(
        source=InvoiceStatusChoices.STATUS_DRAFT,
        target=InvoiceStatusChoices.STATUS_DRAFT,
        label=_("Generate"),
        permission=this.can_generate,
    )
    def generate(self):
        generate_invoice(self.invoice)

    @status.transition(
        source=InvoiceStatusChoices.STATUS_DRAFT,
        target=InvoiceStatusChoices.STATUS_INVOICED,
        label=_("Invoice"),
        permission=this.can_finalize,
    )
    def finalize(self):
        finalize_invoice(self.invoice)

    @status.transition(
        source=InvoiceStatusChoices.STATUS_INVOICED,
        target=InvoiceStatusChoices.STATUS_PAID,
        label=_("Pay"),
        permission=this.can_pay,
    )
    def pay(self):
        pass

    @status.transition(
        source={
            InvoiceStatusChoices.STATUS_DRAFT,
            InvoiceStatusChoices.STATUS_INVOICED,
        },
        target=InvoiceStatusChoices.STATUS_VOID,
        label=_("Void"),
        permission=this.can_void,
    )
    def void(self):
        pass

    def can_generate(self, user):
        return self._check_permission_callbacks("generate", self.invoice, user)

    def can_finalize(self, user):
        return self._check_permission_callbacks("finalize", self.invoice, user)

    def can_pay(self, user):
        return self._check_permission_callbacks("pay", self.invoice, user)

    def can_void(self, user):
        return self._check_permission_callbacks("void", self.invoice, user)


def get_permitted_transition_actions(invoice, user):
    """
    Return a list of ObjectAction instances the user may perform on the given
    invoice, based on its current state. Checks both Django model permissions
    and FSM plugin permission callbacks.
    """
    if not invoice.status:
        return []

    outgoing = InvoiceStatusFlow.status.get_outgoing_transitions(invoice.status)
    action_classes = InvoiceStatusFlow.get_actions([t.slug for t in outgoing])

    permitted = []
    flow = InvoiceStatusFlow(invoice)
    for action in action_classes:
        required_perms = [get_permission_for_model(Invoice, p) for p in action.permissions_required]
        if required_perms and not user.has_perms(required_perms):
            continue
        transition_func = getattr(flow, action.transition)
        if not transition_func.has_perm(user):
            continue
        permitted.append(action)

    return permitted
