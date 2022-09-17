from coldfront.core.allocation.models import Allocation, \
    ClusterAccessRequestStatusChoice, ClusterAccessRequest
from coldfront.core.allocation.models import AllocationAttribute
from coldfront.core.allocation.models import AllocationAttributeType
from coldfront.core.allocation.models import AllocationUser
from coldfront.core.allocation.models import AllocationUserAttribute
from coldfront.core.project.models import Project
from coldfront.core.resource.models import Resource
from django.contrib.auth.models import User
import django_filters


class AllocationAttributeFilter(django_filters.FilterSet):
    """A FilterSet for the AllocationAttribute model."""

    type = django_filters.filters.ModelMultipleChoiceFilter(
        field_name='allocation_attribute_type__name', to_field_name='name',
        queryset=AllocationAttributeType.objects.all())

    class Meta:
        model = AllocationAttribute
        fields = ('type',)


class AllocationFilter(django_filters.FilterSet):
    """A FilterSet for the Allocation model."""

    project = django_filters.filters.ModelMultipleChoiceFilter(
        field_name='project__name', to_field_name='name',
        queryset=Project.objects.all())

    resources = django_filters.filters.ModelMultipleChoiceFilter(
        field_name='resources__name', to_field_name='name',
        queryset=Resource.objects.all())

    class Meta:
        model = Allocation
        fields = ('project', 'resources',)


class AllocationUserAttributeFilter(django_filters.FilterSet):
    """A FilterSet for the AllocationUserAttribute model."""

    type = django_filters.filters.ModelMultipleChoiceFilter(
        field_name='allocation_attribute_type__name', to_field_name='name',
        queryset=AllocationAttributeType.objects.all())

    class Meta:
        model = AllocationUserAttribute
        fields = ('type',)


class AllocationUserFilter(django_filters.FilterSet):
    """A FilterSet for the AllocationUser model."""

    user = django_filters.filters.ModelMultipleChoiceFilter(
        field_name='user__username', to_field_name='username',
        queryset=User.objects.all())

    project = django_filters.filters.ModelMultipleChoiceFilter(
        field_name='allocation__project__name', to_field_name='name',
        queryset=Project.objects.all())

    resources = django_filters.filters.ModelMultipleChoiceFilter(
        field_name='allocation__resources__name', to_field_name='name',
        queryset=Resource.objects.all())

    class Meta:
        model = AllocationUser
        fields = ('project', 'resources',)


class ClusterAccessRequestFilter(django_filters.FilterSet):
    """A FilterSet for the ClusterAccessRequest model."""

    status = django_filters.filters.ModelMultipleChoiceFilter(
        field_name='status__name', to_field_name='name',
        queryset=ClusterAccessRequestStatusChoice.objects.all())

    class Meta:
        model = ClusterAccessRequest
        fields = ('status',)
