from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from coldfront.plugins.slate_project_info.utils import get_slate_project_info_from_ldap


@login_required
def get_slate_project_info(request):
    slate_projects = get_slate_project_info_from_ldap(request.user.username)
    slate_project_list = []
    for slate_project in slate_projects:
        name = slate_project.get('cn')[0]
        access = 'read/write'
        if name.endswith('-ro'):
            name = name[:-len('-ro')]
            access = 'read only'
        owner = slate_project.get('description')[0].split(',')[1].strip().split(' ')[0]

        slate_project_list.append(
            {
                'name': name,
                'access': access,
                'owner': owner
            }
        )

    context = {
        'slate_projects': slate_project_list
    }

    return render(request, "slate_project_info/slate_project_info.html", context)