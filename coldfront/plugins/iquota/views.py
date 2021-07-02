from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.http import HttpResponse

from coldfront.plugins.iquota.utils import Iquota


def get_isilon_quota(request):
    if not request.user.is_authenticated:
        return HttpResponse('401 Unauthorized', status=401)

    username = request.user.username
    groups = [group.name for group in request.user.groups.all()]

    iquota = Iquota(username, groups)

    context = {
        'user_quota': iquota.get_user_quota(),
        'group_quotas': iquota.get_group_quotas(),
    }

    return render(request, "iquota/iquota.html", context)
