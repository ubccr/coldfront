from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from coldfront.core.allocation.models import Allocation
from coldfront.plugins.slate_project import utils


@login_required
def get_slate_project_info(request):
    slate_projects = utils.get_slate_project_info(request.POST.get('viewed_username'))

    context = {
        'slate_projects': slate_projects
    }

    return render(request, "slate_project/slate_project_info.html", context)

def get_slate_project_estimated_cost(request):
    allocation_obj = Allocation.objects.get(pk=request.POST.get('allocation_pk'))

    estimated_cost = utils.get_estimated_storage_cost(allocation_obj)
    context = {'estimated_cost': estimated_cost}

    return render(request, "slate_project/estimated_cost.html", context) 