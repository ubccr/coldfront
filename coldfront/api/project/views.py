import logging

import rest_framework
from django.db import transaction
from django.http import Http404
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework import mixins, status, viewsets

from coldfront.api.permissions import IsAdminUserOrReadOnly, IsSuperuserOrStaff
from coldfront.api.project.filters import ProjectUserRemovalRequestFilter
from coldfront.api.project.serializers import ProjectSerializer, \
    ProjectUserRemovalRequestSerializer
from coldfront.core.project.models import Project, ProjectUserRemovalRequest

from coldfront.core.project.utils_.removal_utils import \
    ProjectRemovalRequestUpdateRunner
from coldfront.core.project.utils_.removal_utils import ProjectRemovalRequestProcessingRunner

authorization_parameter = openapi.Parameter(
    'Authorization',
    openapi.IN_HEADER,
    description=(
        'The authorization token for the requester. The token should be '
        'preceded by "Token " (no quotes).'),
    type=openapi.TYPE_STRING)


logger = logging.getLogger(__name__)


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
    """A ViewSet for the ProjectUserRemovalRequestViewSet model."""

    filterset_class = ProjectUserRemovalRequestFilter
    http_method_names = ['get', 'patch']
    permission_classes = [IsSuperuserOrStaff]
    serializer_class = ProjectUserRemovalRequestSerializer

    def get_queryset(self):
        return ProjectUserRemovalRequest.objects.order_by('id')

    def perform_update(self, serializer):
        try:
            with transaction.atomic():
                instance = serializer.save()
                runner = ProjectRemovalRequestProcessingRunner(instance)
                runner.run()
        except Exception as e:
            logger.exception(e)
            raise APIException('Internal server error.')

    @swagger_auto_schema(
        manual_parameters=[authorization_parameter],
        operation_description=(
            'Updates one or more fields of the ProjectUserRemovalRequest '
            'identified by the given ID.'))
    def partial_update(self, request, *args, **kwargs):
        """The method for PATCH (partial update) requests."""
        return super().partial_update(request, *args, **kwargs)
