from coldfront.core.allocation.models import Allocation
from coldfront.core.allocation.utils import request_project_cluster_access
from coldfront.core.project.models import ProjectUser
from coldfront.core.project.models import ProjectUserJoinRequest
from coldfront.core.project.models import ProjectUserStatusChoice
from coldfront.core.project.utils import get_project_compute_allocation
from coldfront.core.utils.common import import_from_settings
from coldfront.core.utils.mail import send_email_template
from datetime import datetime
from django.conf import settings
from django.core.management.base import BaseCommand
from django.urls import reverse
from urllib.parse import urljoin
import logging
import pytz

"""An admin command that automatically approves user requests to join
projects that have completed their delay period."""


class Command(BaseCommand):

    help = (
        'Automatically approves user requests to join projects that have '
        'completed their delay period.')
    logger = logging.getLogger(__name__)

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):
        pending_status = ProjectUserStatusChoice.objects.get(
            name='Pending - Add')
        active_status = ProjectUserStatusChoice.objects.get(name='Active')
        project_user_objs = ProjectUser.objects.prefetch_related(
            'project', 'project__allocation_set', 'projectuserjoinrequest_set'
        ).filter(status=pending_status)

        num_processed = project_user_objs.count()
        num_successes, num_failures = 0, 0

        now = datetime.utcnow().astimezone(pytz.timezone(settings.TIME_ZONE))

        for project_user_obj in project_user_objs:
            project_obj = project_user_obj.project
            user_obj = project_user_obj.user

            # Retrieve the latest ProjectUserJoinRequest for the ProjectUser.
            try:
                queryset = project_user_obj.projectuserjoinrequest_set
                join_request = queryset.latest('created')
            except ProjectUserJoinRequest.DoesNotExist:
                message = (
                    f'ProjectUser {project_user_obj.pk} has no corresponding '
                    f'ProjectUserJoinRequest.')
                self.stderr.write(self.style.ERROR(message))
                self.logger.error(message)
                num_failures = num_failures + 1
                continue

            # If the request has completed the Project's delay period, auto-
            # approve the user and request cluster access.
            delay = project_obj.joins_auto_approval_delay
            if join_request.created + delay <= now:
                # Retrieve the compute Allocation for the Project.
                try:
                    allocation_obj = get_project_compute_allocation(
                        project_obj)
                except (Allocation.DoesNotExist,
                        Allocation.MultipleObjectsReturned):
                    message = (
                        f'Project {project_obj.name} has no compute '
                        f'allocation.')
                    self.stderr.write(self.style.ERROR(message))
                    self.logger.error(message)
                    num_failures = num_failures + 1
                    continue
                # Set the ProjectUser's status to 'Active'.
                project_user_obj.status = active_status
                project_user_obj.save()
                # Request cluster access for the ProjectUser.
                try:
                    request_project_cluster_access(allocation_obj, user_obj)
                    message = (
                        f'Created a cluster access request for User '
                        f'{user_obj.username} under Project '
                        f'{project_obj.name}.')
                    self.stdout.write(self.style.SUCCESS(message))
                    self.logger.info(message)
                    num_successes = num_successes + 1
                except ValueError:
                    message = (
                        f'User {user_obj.username} already has cluster access '
                        f'under Project {project_obj.name}.')
                    self.stderr.write(self.style.WARNING(message))
                    self.logger.warning(message)
                    num_failures = num_failures + 1
                except Exception as e:
                    message = (
                        f'Failed to request cluster access for User '
                        f'{user_obj.username} under Project '
                        f'{project_obj.name}. Details:')
                    self.stderr.write(self.style.ERROR(message))
                    self.stderr.write(self.style.ERROR(str(e)))
                    self.logger.error(message)
                    self.logger.exception(e)
                    num_failures = num_failures + 1

        if settings.EMAIL_ENABLED:
            self.send_email(num_processed, num_successes, num_failures)

    @staticmethod
    def __review_url():
        """Return the URL to the admin view for reviewing cluster access
        requests."""
        domain = import_from_settings('CENTER_BASE_URL')
        view = reverse('allocation-cluster-account-request-list')
        return urljoin(domain, view)

    def send_email(self, num_processed, num_successes, num_failures):
        """Send an email to admins including the number of requests
        processed, and, of those, how many succeeded and failed."""
        subject = 'New Cluster Access Requests'
        template_name = 'email/new_cluster_access_requests.html'
        context = {
            'num_failures': num_failures,
            'num_processed': num_processed,
            'num_successes': num_successes,
            'review_url': self.__review_url(),
        }
        sender = import_from_settings('EMAIL_SENDER', '')
        receiver_list = [import_from_settings('EMAIL_ADMIN_LIST', '')]
        try:
            send_email_template(
                subject, template_name, context, sender, receiver_list)
        except Exception as e:
            message = 'Failed to send notification email. Details:'
            self.stderr.write(self.style.ERROR(message))
            self.stderr.write(self.style.ERROR(str(e)))
            self.logger.error(message)
            self.logger.exception(e)
