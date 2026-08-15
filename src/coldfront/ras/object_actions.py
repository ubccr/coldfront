# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django.utils.translation import gettext_lazy as _

from coldfront.views.object_actions import ObjectAction


class RequestObject(ObjectAction):
    """
    Perform a Request transition on an object.
    """

    name = "request"
    label = _("Request")
    multi = False
    transition = "request"
    url_kwargs = ["pk"]
    permissions_required = {"request"}
    template_name = "button.request"


class ApproveObject(ObjectAction):
    """
    Perform an Approve transition on an object.
    """

    name = "approve"
    label = _("Approve")
    multi = False
    transition = "approve"
    url_kwargs = ["pk"]
    permissions_required = {"approve"}
    template_name = "button.approve"


class DenyObject(ObjectAction):
    """
    Perform a Deny transition on an object.
    """

    name = "deny"
    label = _("Deny")
    multi = False
    transition = "deny"
    url_kwargs = ["pk"]
    permissions_required = {"deny"}
    template_name = "button.deny"


class ActivateObject(ObjectAction):
    """
    Perform an Activate transition on an object.
    """

    name = "activate"
    label = _("Activate")
    multi = False
    transition = "activate"
    url_kwargs = ["pk"]
    permissions_required = {"activate"}
    template_name = "button.activate"


class RenewObject(ObjectAction):
    """
    Perform a Renew transition on an object.
    """

    name = "renew"
    label = _("Renew")
    multi = False
    transition = "renew"
    url_kwargs = ["pk"]
    permissions_required = {"renew"}
    template_name = "button.renew"


class RevokeObject(ObjectAction):
    """
    Perform a Revoke transition on an object.
    """

    name = "revoke"
    label = _("Revoke")
    multi = False
    transition = "revoke"
    url_kwargs = ["pk"]
    permissions_required = {"revoke"}
    template_name = "button.revoke"


class ReviewObject(ObjectAction):
    """
    Perform a Review transition on an object.
    """

    name = "review"
    label = _("Review")
    multi = False
    transition = "review"
    url_kwargs = ["pk"]
    permissions_required = {"change"}
    template_name = "button.review"


class ApproveChange(ObjectAction):
    """
    Perform an Approve transition on an AllocationChangeRequest.
    """

    name = "approve"
    label = _("Approve Change")
    multi = False
    transition = "approve"
    url_kwargs = ["pk"]
    permissions_required = {"approve"}
    template_name = "button.approve"


class DenyChange(ObjectAction):
    """
    Perform a Deny transition on an AllocationChangeRequest.
    """

    name = "deny"
    label = _("Deny Change")
    multi = False
    transition = "deny"
    url_kwargs = ["pk"]
    permissions_required = {"deny"}
    template_name = "button.deny"


class ApplyChange(ObjectAction):
    """
    Perform an Apply transition on an AllocationChangeRequest.
    """

    name = "apply"
    label = _("Apply Change")
    multi = False
    transition = "apply"
    url_kwargs = ["pk"]
    permissions_required = {"apply"}
    template_name = "button.apply"
