# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0


from django.utils.translation import gettext_lazy as _

from coldfront.views.object_actions import ObjectAction


class SyncQuotaAction(ObjectAction):
    """Sync a quota to backend clusters."""

    name = "sync"
    label = _("Sync Quota")
    template_name = "cf.button.sync"
    url_kwargs = ["pk"]
    permissions_required = {"change"}
