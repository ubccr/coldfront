from datetime import datetime

from django.contrib.auth import get_user_model
from django.test import RequestFactory

from coldfront.config.env import ENV
from coldfront.core.project.models import Project
from coldfront.core.project.views import ProjectStorageReportView
from coldfront.core.utils.common import import_from_settings
from coldfront.core.utils.mail import send_email_template, email_template_context

EMAIL_SENDER = import_from_settings('EMAIL_SENDER')
TESTUSER = ENV.str('TESTUSER')

def send_storage_report_emails():
    """Send monthly email with project storage reports"""
    projects = Project.objects.filter(
        status__name='Active',
        allocation__resources__resource_type__name="Storage",
        allocation__status__name="Active"
    )
    for project in projects:
        send_pdf(project)


def send_pdf(project, context=None):
    """
    Renders the ReportPdfView to PDF and emails it to `to_email`.
    `context` will be passed to the view when rendering.
    """

    system_user = get_user_model().objects.get(username=TESTUSER)
    month = datetime.now().strftime("%B")
    title = project.title
    subject = f'Monthly Coldfront {month} Report for {title}'
    context = email_template_context(extra_context={'project_title': title})
    # 1) build a fake GET request, set any necessary attributes
    factory = RequestFactory()
    request = factory.get(f'project/{project.pk}/report')
    request.user = system_user

    # 2) instantiate and call class‐based view
    view = ProjectStorageReportView.as_view()
    response = view(request, pk=project.pk)

    # 3) make sure the response is rendered and grab the bytes
    if hasattr(response, 'rendered_content'):
        pdf_bytes = response.rendered_content
    else:
        pdf_bytes = response.content

    receivers = project.projectuser_set.filter(role__name__in=['PI','General Manager'])
    receiver_list = [receiver.user.email for receiver in receivers]
    attachment = (f'{title}_{month}_{year}_storagereport.pdf', pdf_bytes, 'application/pdf')
    send_email_template(
        subject, 'email/storage_report.txt', context, EMAIL_SENDER, receiver_list, attachments=(attachment,)
    )
