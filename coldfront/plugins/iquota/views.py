# SPDX-FileCopyrightText: (C) ColdFront Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from django.http import HttpResponse
from django.shortcuts import render

from coldfront.plugins.iquota.utils import Iquota


def get_isilon_quota(request):
    if not request.user.is_authenticated:
        return HttpResponse("401 Unauthorized", status=401)

    username = request.user.username
    groups = [group.name for group in request.user.groups.all()]

    iquota = Iquota(username, groups)

    context = {
        "user_quota": iquota.get_user_quota(),
        "group_quotas": iquota.get_group_quotas(),
    }

    return render(request, "iquota/iquota.html", context)
