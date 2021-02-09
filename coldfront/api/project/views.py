from coldfront.api.permissions import IsAdminUserOrReadOnly
from coldfront.api.project.serializers import ProjectSerializer
from coldfront.core.project.models import Project
from rest_framework import mixins
from rest_framework import viewsets


class ProjectViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin,
                     viewsets.GenericViewSet):
    """A ViewSet for the Project model."""

    filterset_fields = ('name',)
    permission_classes = [IsAdminUserOrReadOnly]
    serializer_class = ProjectSerializer

    def get_queryset(self):
        return Project.objects.all()
