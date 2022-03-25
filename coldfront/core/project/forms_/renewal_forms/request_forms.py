from coldfront.core.allocation.models import AllocationPeriod
from coldfront.core.allocation.models import AllocationRenewalRequest
from coldfront.core.project.forms import DisabledChoicesSelectWidget
from coldfront.core.project.forms_.new_project_forms.request_forms import PooledProjectChoiceField
from coldfront.core.project.models import Project
from coldfront.core.project.models import ProjectUser
from coldfront.core.project.models import ProjectUserRoleChoice
from coldfront.core.project.models import ProjectUserStatusChoice
from coldfront.core.project.models import SavioProjectAllocationRequest

from django import forms


class ProjectRenewalPIChoiceField(forms.ModelChoiceField):

    def label_from_instance(self, obj):
        user = obj.user
        return f'{user.first_name} {user.last_name} ({user.email})'


class ProjectRenewalPISelectionForm(forms.Form):

    PI = ProjectRenewalPIChoiceField(
        label='Principal Investigator',
        queryset=ProjectUser.objects.none(),
        required=True,
        widget=DisabledChoicesSelectWidget())

    def __init__(self, *args, **kwargs):
        self.allocation_period_pk = kwargs.pop('allocation_period_pk', None)
        self.project_pks = kwargs.pop('project_pks', None)
        super().__init__(*args, **kwargs)

        if not (self.allocation_period_pk and self.project_pks):
            return

        role = ProjectUserRoleChoice.objects.get(name='Principal Investigator')
        status = ProjectUserStatusChoice.objects.get(name='Active')

        pi_project_users = ProjectUser.objects.prefetch_related('user').filter(
            project__pk__in=self.project_pks, role=role, status=status
        ).order_by('user__last_name', 'user__first_name')
        users = list(pi_project_users.values_list('user', flat=True))

        allocation_period = AllocationPeriod.objects.get(
            pk=self.allocation_period_pk)
        renewal_request_status_names = ['Under Review', 'Approved', 'Complete']
        pis_with_non_denied_renewal_requests_this_period = set(list(
            AllocationRenewalRequest.objects.filter(
                pi__in=users,
                allocation_period=allocation_period,
                status__name__in=renewal_request_status_names
            ).values_list('pi', flat=True)))

        project_request_status_names = [
            'Under Review', 'Approved - Processing', 'Approved - Complete']
        pis_with_non_denied_project_requests = set(list(
            SavioProjectAllocationRequest.objects.filter(
                status__name__in=project_request_status_names
            ).values_list('pi', flat=True)))

        # Disable any PIs who:
        #     (a) have non-denied AllocationRenewalRequests during this
        #         AllocationPeriod, or
        #     (b) have non-denied SavioProjectAllocationRequests.
        #         TODO: Once the first AllocationPeriod has ended, this will
        #         TODO: need to be refined to filter on time.
        exclude_project_user_pks = set()
        for project_user in pi_project_users:
            if (project_user.user.pk in
                    pis_with_non_denied_renewal_requests_this_period):
                exclude_project_user_pks.add(project_user.pk)
            if (project_user.user.pk in
                    pis_with_non_denied_project_requests):
                exclude_project_user_pks.add(project_user.pk)

        self.fields['PI'].queryset = pi_project_users
        self.fields['PI'].widget.disabled_choices = exclude_project_user_pks


class ProjectRenewalPoolingPreferenceForm(forms.Form):

    UNPOOLED_TO_UNPOOLED = AllocationRenewalRequest.UNPOOLED_TO_UNPOOLED
    UNPOOLED_TO_POOLED = AllocationRenewalRequest.UNPOOLED_TO_POOLED
    POOLED_TO_POOLED_SAME = AllocationRenewalRequest.POOLED_TO_POOLED_SAME
    POOLED_TO_POOLED_DIFFERENT = \
        AllocationRenewalRequest.POOLED_TO_POOLED_DIFFERENT
    POOLED_TO_UNPOOLED_OLD = AllocationRenewalRequest.POOLED_TO_UNPOOLED_OLD
    POOLED_TO_UNPOOLED_NEW = AllocationRenewalRequest.POOLED_TO_UNPOOLED_NEW

    SHORT_DESCRIPTIONS = {
        UNPOOLED_TO_UNPOOLED: 'Stay Unpooled',
        UNPOOLED_TO_POOLED: 'Start Pooling',
        POOLED_TO_POOLED_SAME: 'Stay Pooled, Same Project',
        POOLED_TO_POOLED_DIFFERENT: 'Pool with Different Project',
        POOLED_TO_UNPOOLED_OLD: 'Unpool, Renew Existing Project',
        POOLED_TO_UNPOOLED_NEW: 'Unpool, Create New Project',
    }

    non_pooled_choices = [
        (UNPOOLED_TO_UNPOOLED,
            'Renew the PI\'s allocation under the same project.'),
        (UNPOOLED_TO_POOLED,
            'Pool the PI\'s allocation under a different project.'),
    ]

    pooled_choices = [
        (POOLED_TO_POOLED_SAME,
            'Continuing pooling the PI\'s allocation under the same project.'),
        (POOLED_TO_POOLED_DIFFERENT,
            'Pool the PI\'s allocation under a different project.'),
        (POOLED_TO_UNPOOLED_OLD,
            ('Stop pooling the PI\'s allocation. Select another project owned '
             'by the PI to renew under.')),
        (POOLED_TO_UNPOOLED_NEW,
            ('Stop pooling the PI\'s allocation. Create a new project to '
             'renew under.')),
    ]

    preference = forms.ChoiceField(choices=[], widget=forms.RadioSelect())

    def __init__(self, *args, **kwargs):
        # Raise an exception if 'currently_pooled' is not provided.
        self.currently_pooled = kwargs.pop('currently_pooled')
        super().__init__(*args, **kwargs)
        if self.currently_pooled:
            choices = self.pooled_choices
        else:
            choices = self.non_pooled_choices
        self.fields['preference'].choices = choices


class ProjectRenewalProjectSelectionForm(forms.Form):

    project = PooledProjectChoiceField(
        empty_label=None,
        queryset=Project.objects.none(),
        required=True,
        widget=forms.Select())

    def __init__(self, *args, **kwargs):
        # Raise an exception if any kwargs are not provided.
        for key in ('pi_pk', 'non_owned_projects', 'exclude_project_pk'):
            if key not in kwargs:
                raise KeyError(f'No {key} is provided.')
            else:
                setattr(self, key, kwargs.pop(key))
        super().__init__(*args, **kwargs)

        role = ProjectUserRoleChoice.objects.get(name='Principal Investigator')
        status = ProjectUserStatusChoice.objects.get(name='Active')

        project_pks = list(
            ProjectUser.objects.select_related(
                'project'
            ).filter(
                user__pk=self.pi_pk, role=role, status=status
            ).values_list('project__pk', flat=True))

        _filter = {'name__startswith': 'fc_'}
        exclude = {'pk': self.exclude_project_pk}
        if self.non_owned_projects:
            # # Only include Projects where this user is not a PI.
            # exclude['pk__in'] = project_pks
            # A PI may wish to pool their allocation under a Project they are
            # already a PI on. Allow this.
            pass
        else:
            # Only include Projects where this user is a PI.
            _filter['pk__in'] = project_pks
        self.fields['project'].queryset = Project.objects.filter(
            **_filter).exclude(**exclude).order_by('name')


class ProjectRenewalReviewAndSubmitForm(forms.Form):

    confirmation = forms.BooleanField(
        label=(
            'I have reviewed my selections and understand the changes '
            'described above. Submit my request.'),
        required=True)
