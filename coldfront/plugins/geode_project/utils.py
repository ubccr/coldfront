from django.urls import reverse

from coldfront.core.utils.mail import build_link, send_email_template, email_template_context
from coldfront.core.utils.common import import_from_settings

EMAIL_ENABLED = import_from_settings('EMAIL_ENABLED')
if EMAIL_ENABLED:
    EMAIL_SENDER = import_from_settings('EMAIL_SENDER')
    GEODE_PROJECT_EMAIL = import_from_settings('GEODE_PROJECT_EMAIL')

def send_new_allocation_request_email(project_obj):
    allocation_objs = project_obj.allocation_set.filter(resources__name='Geode-Projects', status__name='New')
    for allocation_obj in allocation_objs:
        if EMAIL_ENABLED:
            template_context = email_template_context()
            template_context['pi'] = project_obj.pi.username
            template_context['resource'] = allocation_obj.get_parent_resource
            template_context['url'] = build_link(reverse('allocation-detail', kwargs={'pk': allocation_obj.pk}))
            template_context['project_title'] = project_obj.title
            template_context['project_detail_url'] = build_link(reverse('project-detail', kwargs={'pk': project_obj.pk}))
            template_context['project_id'] = project_obj.pk
            send_email_template(
                f'New Allocation Request: {project_obj.pi.username} - {allocation_obj.get_parent_resource}',
                'email/new_allocation_request.txt',
                template_context,
                EMAIL_SENDER,
                [GEODE_PROJECT_EMAIL, ],
            )
