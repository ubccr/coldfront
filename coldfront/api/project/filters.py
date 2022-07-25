from coldfront.core.project.models import \
    ProjectUserRemovalRequestStatusChoice, ProjectUserRemovalRequest
import django_filters.filters


class ProjectUserRemovalRequestFilter(django_filters.FilterSet):
    """A FilterSet for the ProjectUserRemovalRequest model."""

    status = django_filters.filters.ModelMultipleChoiceFilter(
        field_name='status__name', to_field_name='name',
        queryset=ProjectUserRemovalRequestStatusChoice.objects.all())

    class Meta:
        model = ProjectUserRemovalRequest
        fields = ('status',)
