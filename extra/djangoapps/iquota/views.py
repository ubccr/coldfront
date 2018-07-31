from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from extra.djangoapps.iquota.utils import Iquota


@login_required
def get_isilon_quota(request):

    username = request.user.username
    groups = [group.name for group in request.user.groups.all()]

    iquota = Iquota(username, groups)

    context = {
        'user_quota': iquota.get_user_quota(),
        'group_quotas': iquota.get_group_quotas(),
    }

    return render(request, "iquota/iquota.html", context)
