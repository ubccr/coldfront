from django import forms
from django.shortcuts import get_object_or_404

from core.djangoapps.project.models import Project, ProjectUserRoleChoice, ProjectReview
import datetime
from common.djangolibs.utils import import_from_settings

EMAIL_DIRECTOR_PENDING_PROJECT_REVIEW_EMAIL = import_from_settings('EMAIL_DIRECTOR_PENDING_PROJECT_REVIEW_EMAIL')


class ProjectSearchForm(forms.Form):
    """ Search form for the Project list page.
    """
    LAST_NAME = 'Last Name'
    USERNAME = 'Username'
    FIELD_OF_SCIENCE = 'Field of Science'

    last_name = forms.CharField(label=LAST_NAME, max_length=100, required=False)
    username = forms.CharField(label=USERNAME, max_length=100, required=False)
    field_of_science=forms.CharField(label=FIELD_OF_SCIENCE, max_length=100, required=False)
    show_all_projects=forms.BooleanField(initial=False, required=False)


class ProjectAddUserForm(forms.Form):
    username = forms.CharField(max_length=150, disabled=True)
    first_name = forms.CharField(max_length=30, required=False, disabled=True)
    last_name = forms.CharField(max_length=150, required=False, disabled=True)
    email = forms.EmailField(max_length=100, required=False, disabled=True)
    source = forms.CharField(max_length=16, disabled=True)
    role = forms.ModelChoiceField(queryset=ProjectUserRoleChoice.objects.all(), empty_label=None)
    selected = forms.BooleanField(initial=False, required=False)


class ProjectAddUsersToSubscriptionForm(forms.Form):
    subscription = forms.MultipleChoiceField(widget=forms.CheckboxSelectMultiple, required=False)

    def __init__(self, request_user, project_pk, *args, **kwargs):
        super().__init__(*args, **kwargs)
        project_obj = get_object_or_404(Project, pk=project_pk)

        subscription_query_set = project_obj.subscription_set.filter(
            status__name__in=['Active', 'New', 'Pending'])
        subscription_choices = [(subscription.id, "%s (%s)" %(subscription.resources.first().name, subscription.resources.first().resource_type.name)) for subscription in subscription_query_set]
        subscription_choices.insert(0, ('__select_all__', 'Select All'))
        if subscription_query_set:
            self.fields['subscription'].choices = subscription_choices
            self.fields['subscription'].help_text = '<br/>Select subscriptions to add selected users to.'
        else:
            self.fields['subscription'].widget = forms.HiddenInput()


class ProjectRemoveUserForm(forms.Form):
    username = forms.CharField( max_length=150, disabled=True)
    first_name = forms.CharField(max_length=30, required=False, disabled=True)
    last_name = forms.CharField(max_length=150, required=False, disabled=True)
    email = forms.EmailField(max_length=100, required=False, disabled=True)
    role = forms.CharField(max_length=30, disabled=True)
    selected = forms.BooleanField(initial=False, required=False)


class ProjectUserUpdateForm(forms.Form):
    role = forms.ModelChoiceField(queryset=ProjectUserRoleChoice.objects.all(), empty_label=None)
    enable_notifications = forms.BooleanField(initial=False, required=False)


class ProjectReviewForm(forms.Form):
    reason = forms.CharField(widget=forms.Textarea, required=False)
    acknowledgement = forms.BooleanField(label='By checking this box I acknowledge that I have updated my project to the best of my knowledge', initial=False, required=True)

    def __init__(self, project_pk, *args, **kwargs):
        super().__init__(*args, **kwargs)
        project_obj = get_object_or_404(Project, pk=project_pk)
        now = datetime.datetime.now(datetime.timezone.utc)

        if project_obj.grant_set.exists():
            latest_grant = project_obj.grant_set.order_by('-modified')[0]
            grant_updated_in_last_year = (now - latest_grant.created).days < 365
        else:
            grant_updated_in_last_year = None

        if project_obj.publication_set.exists():
            latest_publication = project_obj.publication_set.order_by('-created')[0]
            publication_updated_in_last_year = (now - latest_publication.created).days < 365
        else:
            publication_updated_in_last_year = None

        if grant_updated_in_last_year and publication_updated_in_last_year:
            self.fields['reason'].widget = forms.HiddenInput()
        else:
            self.fields['reason'].required = True


        self.fields['reason'].help_text = '<br/>Reason for not adding new grants and/or publications in the past year.'



class ProjectReviewEmailForm(forms.Form):
    email_body = forms.CharField(
        required=True,
        widget=forms.Textarea
    )

    def __init__(self, pk, *args, **kwargs):
        super().__init__(*args, **kwargs)
        project_review_obj = get_object_or_404(ProjectReview, pk=int(pk))
        self.fields['email_body'].initial = 'Dear {} {} \n{}'.format(project_review_obj.project.pi.first_name, project_review_obj.project.pi.last_name, EMAIL_DIRECTOR_PENDING_PROJECT_REVIEW_EMAIL)
