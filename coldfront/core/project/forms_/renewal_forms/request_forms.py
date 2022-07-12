from coldfront.core.allocation.models import AllocationPeriod
from coldfront.core.allocation.models import AllocationRenewalRequest
from coldfront.core.project.forms import DisabledChoicesSelectWidget
from coldfront.core.project.forms_.new_project_forms.request_forms import PooledProjectChoiceField
from coldfront.core.project.models import Project
from coldfront.core.project.models import ProjectUser
from coldfront.core.project.models import ProjectUserRoleChoice
from coldfront.core.project.models import ProjectUserStatusChoice
from coldfront.core.project.utils_.new_project_utils import non_denied_new_project_request_statuses
from coldfront.core.project.utils_.new_project_utils import pis_with_new_project_requests_pks
from coldfront.core.project.utils_.renewal_utils import non_denied_renewal_request_statuses
from coldfront.core.project.utils_.renewal_utils import pis_with_renewal_requests_pks
from coldfront.core.resource.utils_.allowance_utils.computing_allowance import ComputingAllowance
from coldfront.core.resource.utils_.allowance_utils.interface import ComputingAllowanceInterface

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
        self.computing_allowance = kwargs.pop('computing_allowance', None)
        self.allocation_period_pk = kwargs.pop('allocation_period_pk', None)
        self.project_pks = kwargs.pop('project_pks', None)
        super().__init__(*args, **kwargs)

        if not (self.computing_allowance and self.allocation_period_pk
                and self.project_pks):
            return

        self.computing_allowance = ComputingAllowance(self.computing_allowance)
        self.allocation_period = AllocationPeriod.objects.get(
            pk=self.allocation_period_pk)

        role = ProjectUserRoleChoice.objects.get(name='Principal Investigator')
        status = ProjectUserStatusChoice.objects.get(name='Active')

        pi_project_users = ProjectUser.objects.prefetch_related('user').filter(
            project__pk__in=self.project_pks, role=role, status=status
        ).order_by('user__last_name', 'user__first_name')

        self.fields['PI'].queryset = pi_project_users
        self.disable_pi_choices(pi_project_users)

    def disable_pi_choices(self, pi_project_users):
        """Prevent certain of the given ProjectUsers, who should be
        displayed, from being selected for renewal."""
        disable_project_user_pks = set()
        if self.computing_allowance.is_one_per_pi():
            # Disable any PI who has:
            #    (a) a new project request for a Project during the
            #        AllocationPeriod*, or
            #    (b) an AllocationRenewalRequest during the AllocationPeriod*.
            # * Requests must have ineligible statuses.
            resource = self.computing_allowance.get_resource()
            disable_user_pks = set()
            new_project_request_status_names = list(
                non_denied_new_project_request_statuses().values_list(
                    'name', flat=True))
            disable_user_pks.update(
                pis_with_new_project_requests_pks(
                    self.allocation_period,
                    computing_allowance=resource,
                    request_status_names=new_project_request_status_names))
            renewal_request_status_names = list(
                non_denied_renewal_request_statuses().values_list(
                    'name', flat=True))
            disable_user_pks.update(
                pis_with_renewal_requests_pks(
                    self.allocation_period,
                    computing_allowance=resource,
                    request_status_names=renewal_request_status_names))
            for project_user in pi_project_users:
                if project_user.user.pk in disable_user_pks:
                    disable_project_user_pks.add(project_user.pk)
        self.fields['PI'].widget.disabled_choices = disable_project_user_pks


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
            'Renew the PI\'s allowance under the same project.'),
        (UNPOOLED_TO_POOLED,
            'Pool the PI\'s allowance under a different project.'),
    ]

    pooled_choices = [
        (POOLED_TO_POOLED_SAME,
            'Continue pooling the PI\'s allowance under the same project.'),
        (POOLED_TO_POOLED_DIFFERENT,
            'Pool the PI\'s allowance under a different project.'),
        (POOLED_TO_UNPOOLED_OLD,
            ('Stop pooling the PI\'s allowance. Select another project owned '
             'by the PI to renew under.')),
        (POOLED_TO_UNPOOLED_NEW,
            ('Stop pooling the PI\'s allowance. Create a new project to '
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
        self.computing_allowance = kwargs.pop('computing_allowance', None)
        # Raise an exception if certain kwargs are not provided.
        for key in ('pi_pk', 'non_owned_projects', 'exclude_project_pk'):
            if key not in kwargs:
                raise KeyError(f'No {key} is provided.')
            else:
                setattr(self, key, kwargs.pop(key))
        super().__init__(*args, **kwargs)

        if not self.computing_allowance:
            return
        computing_allowance_interface = ComputingAllowanceInterface()
        self.computing_allowance = ComputingAllowance(self.computing_allowance)

        role = ProjectUserRoleChoice.objects.get(name='Principal Investigator')
        status = ProjectUserStatusChoice.objects.get(name='Active')

        project_pks = list(
            ProjectUser.objects.select_related(
                'project'
            ).filter(
                user__pk=self.pi_pk, role=role, status=status
            ).values_list('project__pk', flat=True))

        _filter = {
            'name__startswith': computing_allowance_interface.code_from_name(
                self.computing_allowance.get_name()),
        }
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
