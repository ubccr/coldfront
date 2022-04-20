from coldfront.core.project.models import ProjectUser
from django.db.models import Q


def allocation_navbar_visibility(request):
    """Set the following context variables:
        - ALLOCATION_VISIBLE: Whether the allocation tab should be
          visible to the requesting user."""
    allocation_key = 'ALLOCATION_VISIBLE'
    context = {
        allocation_key: False,
    }

    if not request.user.is_authenticated:
        return context

    # Allocation list view should be visible to superusers and staff.
    if request.user.is_superuser or request.user.is_staff:
        context[allocation_key] = True
        return context

    # Allocation list view should be visible to active PIs and Managers.
    project_user = ProjectUser.objects.filter(
        Q(role__name__in=['Manager', 'Principal Investigator']) &
        Q(status__name='Active') &
        Q(user=request.user))
    context[allocation_key] = project_user.exists()

    return context
