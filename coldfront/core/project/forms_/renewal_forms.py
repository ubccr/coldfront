from coldfront.core.project.forms import DisabledChoicesSelectWidget
from coldfront.core.project.forms import PooledProjectChoiceField
from coldfront.core.project.models import Project
from coldfront.core.project.models import ProjectUser
from coldfront.core.project.models import ProjectUserRoleChoice
from coldfront.core.project.models import ProjectUserStatusChoice

from django import forms


class ProjectRenewalPIChoiceField(forms.ModelChoiceField):

    def label_from_instance(self, obj):
        user = obj.user
        return f'{user.first_name} {user.last_name} ({user.email})'


class SavioProjectRenewalRequestForm(forms.Form):

    PI = ProjectRenewalPIChoiceField(
        label='Principal Investigator',
        queryset=ProjectUser.objects.none(),
        required=True,
        widget=DisabledChoicesSelectWidget())

    def __init__(self, *args, **kwargs):
        self.allocation_period_pk = kwargs.pop('allocation_period_pk', None)
        self.project_pk = kwargs.pop('project_pk', None)
        super().__init__(*args, **kwargs)

        project = Project.objects.get(pk=self.project_pk)
        role = ProjectUserRoleChoice.objects.get(
            name='Principal Investigator')
        status = ProjectUserStatusChoice.objects.get(name='Active')
        pi_project_users = project.projectuser_set.filter(role=role)

        # Disable any PIs who are inactive or who have already renewed their
        # allocations during this allocation period.
        exclude_project_user_pks = set()
        for project_user in pi_project_users:
            if project_user.status != status:
                exclude_project_user_pks.add(project_user.pk)
            # TODO

        self.fields['PI'].queryset = pi_project_users
        self.fields['PI'].widget.disabled_choices = exclude_project_user_pks


# TODO: Combine this with the above if possible.
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

        role = ProjectUserRoleChoice.objects.get(name='Principal Investigator')
        status = ProjectUserStatusChoice.objects.get(name='Active')

        pi_project_users = ProjectUser.objects.filter(
            project__pk__in=self.project_pks, role=role, status=status)

        # Disable any PIs who are inactive or who have already renewed their
        # allocations during this allocation period.
        exclude_project_user_pks = set()
        for project_user in pi_project_users:
            if project_user.status != status:
                exclude_project_user_pks.add(project_user.pk)
            # TODO

        self.fields['PI'].queryset = pi_project_users
        self.fields['PI'].widget.disabled_choices = exclude_project_user_pks


class ProjectRenewalPoolingPreferenceForm(forms.Form):

    non_pooled_choices = [
        ('renew_unpooled',
            'Renew the PI\'s allocation under the same project.'),
        ('pool', 'Pool the PI\'s allocation under a different project.'),
    ]

    pooled_choices = [
        ('pool_with_same',
            'Continuing pooling the PI\'s allocation under the same project.'),
        ('pool_with_different',
            'Pool the PI\'s allocation under a different project.'),
        ('unpool_renew_existing',
            ('Stop pooling the PI\'s allocation. Select another project owned '
             'by the PI to renew under.')),
        ('unpool_create_new',
            'Stop pooling the PI\'s allocation. Create a new project.'),
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

        # TODO: Handle other allocation types.
        _filter = {'name__startswith': 'fc_'}
        exclude = {'pk': self.exclude_project_pk}
        if self.non_owned_projects:
            # Only include Projects where this user is not a PI.
            exclude['pk__in'] = project_pks
        else:
            # Only include Projects where this user is a PI.
            _filter['pk__in'] = project_pks
        self.fields['project'].queryset = Project.objects.filter(
            **_filter).exclude(**exclude).order_by('name')


class ProjectRenewalReviewAndSubmitForm(forms.Form):

    # TODO: Figure out what fields to display here.
    # TODO: Disable all fields.
    # TODO: Display the pro-rated allocation amount.

    pass
