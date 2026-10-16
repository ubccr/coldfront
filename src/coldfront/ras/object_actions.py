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
    icon = "tablericon.git-pull-request"
    variant = "primary"
    as_ = "a"
    multi = False
    transition = "request"
    url_kwargs = ["pk"]
    permissions_required = {"request"}


class ApproveObject(ObjectAction):
    """
    Perform an Approve transition on an object.
    """

    name = "approve"
    label = _("Approve")
    icon = "heroicon.shield-check"
    variant = "success"
    modal = True
    multi = False
    transition = "approve"
    url_kwargs = ["pk"]
    permissions_required = {"approve"}


class DenyObject(ObjectAction):
    """
    Perform a Deny transition on an object.
    """

    name = "deny"
    label = _("Deny")
    icon = "tablericon.forbid"
    variant = "error"
    modal = True
    multi = False
    transition = "deny"
    url_kwargs = ["pk"]
    permissions_required = {"deny"}


class ActivateObject(ObjectAction):
    """
    Perform an Activate transition on an object.
    """

    name = "activate"
    label = _("Activate")
    icon = "tablericon.player-play"
    variant = "primary"
    as_ = "a"
    multi = False
    transition = "activate"
    url_kwargs = ["pk"]
    permissions_required = {"activate"}


class RenewObject(ObjectAction):
    """
    Perform a Renew transition on an object.
    """

    name = "renew"
    label = _("Renew")
    icon = "tablericon.refresh"
    variant = "primary"
    modal = True
    multi = False
    transition = "renew"
    url_kwargs = ["pk"]
    permissions_required = {"renew"}


class RevokeObject(ObjectAction):
    """
    Perform a Revoke transition on an object.
    """

    name = "revoke"
    label = _("Revoke")
    icon = "tablericon.player-stop"
    variant = "error"
    modal = True
    multi = False
    transition = "revoke"
    url_kwargs = ["pk"]
    permissions_required = {"revoke"}


class ReviewObject(ObjectAction):
    """
    Perform a Review transition on an object.
    """

    name = "review"
    label = _("Review")
    icon = "heroicon.eye"
    variant = "warning"
    modal = True
    multi = False
    transition = "review"
    url_kwargs = ["pk"]
    permissions_required = {"change"}


class ApproveChange(ObjectAction):
    """
    Perform an Approve transition on an AllocationChangeRequest.
    """

    name = "approve"
    label = _("Approve Change")
    icon = "heroicon.check-circle"
    variant = "success"
    modal = True
    multi = False
    transition = "approve"
    url_kwargs = ["pk"]
    permissions_required = {"approve"}


class DenyChange(ObjectAction):
    """
    Perform a Deny transition on an AllocationChangeRequest.
    """

    name = "deny"
    label = _("Deny Change")
    icon = "tablericon.forbid"
    variant = "error"
    modal = True
    multi = False
    transition = "deny"
    url_kwargs = ["pk"]
    permissions_required = {"deny"}


class ApplyChange(ObjectAction):
    """
    Perform an Apply transition on an AllocationChangeRequest.
    """

    name = "apply"
    label = _("Apply Change")
    icon = "tablericon.player-play"
    variant = "primary"
    modal = True
    multi = False
    transition = "apply"
    url_kwargs = ["pk"]
    permissions_required = {"apply"}
