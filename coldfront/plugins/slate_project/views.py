from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from coldfront.plugins.slate_project import utils


@login_required
def get_slate_project_info(request):
    slate_projects = utils.get_slate_project_info(request.POST.get('viewed_username'))

    context = {
        'slate_projects': slate_projects
    }

    return render(request, "slate_project/slate_project_info.html", context)