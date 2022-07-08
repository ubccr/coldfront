import logging

import rest_framework
from django.db import transaction
from django.http import Http404
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework.response import Response
from rest_framework import mixins, status, viewsets

from coldfront.api.permissions import IsAdminUserOrReadOnly, IsSuperuserOrStaff
from coldfront.api.project.filters import ProjectUserRemovalRequestFilter
from coldfront.api.project.serializers import ProjectSerializer, \
    ProjectUserRemovalRequestSerializer
from coldfront.core.project.models import Project, ProjectUserRemovalRequest

from coldfront.core.project.utils_.removal_utils import \
    ProjectRemovalRequestUpdateRunner

authorization_parameter = openapi.Parameter(
    'Authorization',
    openapi.IN_HEADER,
    description=(
        'The authorization token for the requester. The token should be '
        'preceded by "Token " (no quotes).'),
    type=openapi.TYPE_STRING)


class ProjectViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin,
                     viewsets.GenericViewSet):
    """A ViewSet for the Project model."""

    filterset_fields = ('name',)
    permission_classes = [IsAdminUserOrReadOnly]
    serializer_class = ProjectSerializer

    def get_queryset(self):
        return Project.objects.all()


class ProjectUserRemovalRequestViewSet(mixins.ListModelMixin,
                                       mixins.RetrieveModelMixin,
                                       mixins.UpdateModelMixin,
                                       viewsets.GenericViewSet):
    """A ViewSet for the IdentityLinkingRequest model."""

    filterset_class = ProjectUserRemovalRequestFilter
    http_method_names = ['get', 'patch']
    permission_classes = [IsSuperuserOrStaff]
    serializer_class = ProjectUserRemovalRequestSerializer

    def get_queryset(self):
        return ProjectUserRemovalRequest.objects.order_by('id')

    @swagger_auto_schema(
        manual_parameters=[authorization_parameter],
        operation_description=(
            'Updates one or more fields of the ProjectUserRemovalRequest '
            'identified by the given ID.'),
        auto_schema=None)
    @transaction.atomic
    def partial_update(self, request, *args, **kwargs):
        """The method for PATCH (partial update) requests."""
        logger = logging.getLogger(__name__)

        partial = kwargs.pop('partial', False)
        try:
            instance = self.get_object()
            serializer = self.get_serializer(
                instance, data=request.data, partial=partial)

        except Http404:
            serializer = self.get_serializer(
                data=request.data, partial=partial)

        try:
            serializer.is_valid(raise_exception=True)

            status_name = serializer.validated_data['status'].name
            completion_time = serializer.validated_data.get('completion_time', None)
            runner = \
                ProjectRemovalRequestUpdateRunner(instance)
            runner.update_request(status_name)
            if status_name == 'Complete':
                runner.update_request(status_name)
                runner.complete_request(completion_time=completion_time)
                runner.send_emails()
            elif status_name in ['Pending', 'Processing']:
                runner.update_request(status_name)

            return Response(serializer.data,
                            status=rest_framework.status.HTTP_200_OK)

        except Exception as e:
            logger.exception(f'Failed to update the status of the removal '
                             f'request {kwargs["pk"]}.')

        return Response(serializer.errors,
                        status=rest_framework.status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(
        manual_parameters=[authorization_parameter],
        operation_description=(
                'Updates all fields of the ProjectUserRemovalRequest '
                'identified by the given ID.'),
        auto_schema=None)
    @transaction.atomic
    def update(self, request, *args, **kwargs):
        """The method for PUT (update) requests."""
        return Response({'failure': 'This method is not supported.'})

    @swagger_auto_schema(
        manual_parameters=[authorization_parameter],
        operation_description=(
                'Creates a new ProjectUserRemovalRequest identified by the '
                'given ID.'))
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        """The method for POST (create) requests."""
        return Response({'failure': 'This method is not supported.'})

    @swagger_auto_schema(
        manual_parameters=[authorization_parameter],
        operation_description=(
                'Deletes a ProjectUserRemovalRequest identified by the '
                'given ID.'))
    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        """The method for DELETE (destroy) requests."""
        return Response({'failure': 'This method is not supported.'})