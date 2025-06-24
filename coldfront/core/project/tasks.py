from io import BytesIO
from datetime import datetime

from django.http import FileResponse, HttpResponse
from django.test import RequestFactory
from django.conf import settings

# import your report view

from coldfront.core.project.models import Project
from coldfront.core.project.views import ProjectStorageReportView
from coldfront.core.utils.common import import_from_settings
from coldfront.core.utils.mail import send_email_template, email_template_context

EMAIL_SENDER = import_from_settings('EMAIL_SENDER')

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

    month = datetime.now().strftime("%B")
    title = project.title
    subject = f'Monthly Coldfront {month} Report for {title}'
    context = email_template_context(extra_context={'project_title': title})
    # 1) build a fake GET request, set any attributes your view needs (e.g. user)
    factory = RequestFactory()
    request = factory.get(f'project/{project.pk}/report')
    request.user = getattr(context or {}, 'user', None)

    # 2) instantiate and call your class‐based view
    #    if you are using a simple function‐based view, just call it
    view = ProjectStorageReportView.as_view()
    response = view(request, **(context or {}))

    # 3) make sure the response is rendered and grab the bytes
    #    PDFTemplateResponseMixin often provides `.rendered_content`
    if hasattr(response, 'rendered_content'):
        pdf_bytes = response.rendered_content
    else:
        # fallback
        pdf_bytes = response.content

    receivers = project.projectuser_set.filter(role__name__in=['PI','General Manager'])
    receiver_list = [receiver.user.email for receiver in receivers]
    send_email_template(
        subject, 'storage_report.txt', context, EMAIL_SENDER, receiver_list, attachments=(pdf_bytes)
    )
