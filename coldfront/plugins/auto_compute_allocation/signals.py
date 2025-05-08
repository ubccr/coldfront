import logging

from django.dispatch import receiver
from django_q.tasks import async_task

from coldfront.core.project.models import Project
from coldfront.core.project.signals import project_new
from coldfront.core.project.views import ProjectCreateView
from coldfront.core.utils.common import import_from_settings
from coldfront.plugins.auto_compute_allocation.tasks import add_auto_compute_allocation

logger = logging.getLogger(__name__)

PROJECT_CODE = import_from_settings('PROJECT_CODE', False)

@receiver(project_new, sender=ProjectCreateView)
def project_new_auto_compute_allocation(sender, **kwargs):
    if PROJECT_CODE:
        project_obj = kwargs.get('project_obj')
        # Add a compute allocation
        async_task('coldfront.plugins.auto_compute_allocation.tasks.add_auto_compute_allocation', project_obj)
    else:
        logger.info("WARNING: PROJECT_CODE not enabled, will not call task for auto_compute_allocation")