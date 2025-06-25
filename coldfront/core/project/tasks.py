from coldfront.config.env import ENV
from coldfront.core.project.models import Project
from coldfront.core.project.utils import send_storagereport_pdf
from coldfront.core.utils.common import import_from_settings

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
        send_storagereport_pdf(project)
