from coldfront.core.allocation.models import Allocation
from coldfront.core.resource.models import Resource
from django.core.exceptions import ValidationError
from django.db.models.signals import m2m_changed
import django.dispatch

allocation_activate_user = django.dispatch.Signal(
    providing_args=["allocation_user_pk"])
allocation_remove_user = django.dispatch.Signal(
    providing_args=["allocation_user_pk"])


@django.dispatch.receiver(m2m_changed, sender=Allocation.resources.through)
def allocation_resources_changed(sender, **kwargs):
    """Handle changes to an Allocation's Resources.

    In particular, before a new Resource is added, if that Resource is
    unique-per-project, raise an error if the Project already has an
    Allocation to the Resource.

    Parameters:
        - sender (Allocation_resources): a relationship between the
        Allocation and its Resources
        - kwargs (dict): a dictionary with 'action' and 'pk_set' keys

    Returns:
        - None

    Raises:
        - ValidationError, if the Resource is unique-per-project and the
        Allocation's Project has an existing Allocation to it
    """
    instance = kwargs.pop('instance', None)
    pk_set = kwargs.pop('pk_set', None)
    action = kwargs.pop('action', None)
    if action == 'pre_add':
        project = instance.project
        for pk in pk_set:
            resource = Resource.objects.get(pk=pk)
            if not resource.is_unique_per_project:
                continue
            allocations = project.allocation_set.exclude(
                pk=instance.pk).filter(resources=resource)
            if allocations.exists():
                raise ValidationError(
                    f'Project {project.pk} has an existing Allocation '
                    f'({allocations.first().pk}) to unique-per-project '
                    f'Resource {resource.pk}.')
