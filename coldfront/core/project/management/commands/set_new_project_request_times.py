from coldfront.core.project.models import HistoricalSavioProjectAllocationRequest
from coldfront.core.project.models import ProjectAllocationRequestStatusChoice
from coldfront.core.project.models import SavioProjectAllocationRequest

from django.core.management.base import BaseCommand


"""An admin command that sets the request, approval, and completion
times for SavioProjectAllocationRequests from historical objects."""


class Command(BaseCommand):

    help = (
        'Set request, approval, and completion times for'
        'SavioProjectAllocationRequests from historical objects.')

    def handle(self, *args, **options):
        """Set request_time, approval_time, and completion_time fields
        for each SavioProjectAllocationRequest in the database."""
        approved_processing_status = \
            ProjectAllocationRequestStatusChoice.objects.get(
                name='Approved - Processing')
        approved_complete_status = \
            ProjectAllocationRequestStatusChoice.objects.get(
                name='Approved - Complete')
        for request in SavioProjectAllocationRequest.objects.all():
            # Set the request_time to be the time at which the object was
            # created.
            request.request_time = request.created
            # Set the approval_time to be the first datetime at which the
            # object had the 'Approved - Processing' status, if any.
            historical_objects_processed = \
                HistoricalSavioProjectAllocationRequest.objects.filter(
                    id=request.id,
                    status=approved_processing_status).order_by('history_date')
            if historical_objects_processed.exists():
                request.approval_time = \
                    historical_objects_processed.first().history_date
            # Set the completion_time to be the first datetime at which the
            # object had the 'Approved - Complete' status, if any.
            historical_objects_complete = \
                HistoricalSavioProjectAllocationRequest.objects.filter(
                    id=request.id,
                    status=approved_complete_status).order_by('history_date')
            if historical_objects_complete.exists():
                request.completion_time = \
                    historical_objects_complete.first().history_date
            request.save()
