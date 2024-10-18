from django.dispatch import receiver

from coldfront.core.project.signals import project_activate
from coldfront.core.project.views import ProjectActivateRequestView
from coldfront.core.project.models import Project
from coldfront.plugins.geode_project.utils import send_new_allocation_request_email


@receiver(project_activate, sender=ProjectActivateRequestView)
def send_allocation_request_email(sender, **kwargs):
    project_pk = kwargs.get('project_pk')
    project_obj = Project.objects.get(pk=project_pk)

    send_new_allocation_request_email(project_obj)
