from django.contrib.auth.models import Group


def mirror_groups(backend, user, response, *args, **kwargs):
    groups = response.get('groups')
    user.groups.clear()
    for group_name in groups.split(';'):
        group, created = Group.objects.get_or_create(name=group_name)
        user.groups.add(group)
