# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0


from django.utils.translation import gettext_lazy as _

from coldfront.lib.views.object_actions import ObjectAction


class SyncQuotaAction(ObjectAction):
    """Sync a quota to backend clusters."""

    name = "sync"
    label = _("Sync Quota")
    icon = "tablericon.refresh"
    variant = "info"
    modal = True
    url_kwargs = ["pk"]
    permissions_required = {"change"}
