from re import T
from django import forms
from django.forms import ModelForm
from django.shortcuts import get_object_or_404

from coldfront.core.project.models import Project
from coldfront.core.grant.models import Grant
from coldfront.core.utils.common import import_from_settings

PLUGIN_ORCID = import_from_settings('PLUGIN_ORCID', False)
if PLUGIN_ORCID:
    ORCID_SANDBOX = import_from_settings('ORCID_SANDBOX', True)

CENTER_NAME = import_from_settings('CENTER_NAME')


class GrantForm(ModelForm):
    class Meta:
        model = Grant
        exclude = ['project', ]
        labels = {
            'percent_credit': 'Percent credit to {}'.format(CENTER_NAME),
            'direct_funding': 'Direct funding to {}'.format(CENTER_NAME)
        }
        help_texts = {
            'percent_credit': 'Percent credit as entered in the sponsored projects form for grant submission as financial credit to the department/unit in the credit distribution section',
            'direct_funding': 'Funds budgeted specifically for {} services, hardware, software, and/or personnel'.format(CENTER_NAME)
        }

    def __init__(self, *args, **kwargs):
        super(GrantForm, self).__init__(*args, **kwargs) 
        self.fields['funding_agency'].queryset = self.fields['funding_agency'].queryset.order_by('name')


class OrcidImportGrantQueryForm(forms.Form):
     users = forms.MultipleChoiceField(
        widget=forms.CheckboxSelectMultiple, required=False)
        

     def __init__(self, project_pk,  *args, **kwargs):
        super().__init__(*args, **kwargs)
        project_obj = get_object_or_404(Project, pk=project_pk)
        user_query_set = project_obj.projectuser_set.select_related('user').filter(
            status__name__in=['Active', ]).order_by("user__username")
        if user_query_set:
            user_choices = []
            for project_user in user_query_set:
                try:
                    user = project_user.user 
                    if ORCID_SANDBOX: 
                        orcid_is_linked = user.social_auth.get(provider='orcid-sandbox')
                    else:
                        orcid_is_linked = user.social_auth.get(provider='orcid')
                    if project_obj.pi == user:
                        user_choices.append((user.username, f"You ({user.username})"))
                    else:
                        user_choices.append((user.username, f"{user.first_name} {user.last_name} ({user.username})"))
                except:
                    pass
            self.fields['users'].choices = user_choices
            self.fields['users'].help_text = '<br/>Select users in your project to pull their ORCID grant information.'
        else:
            self.fields['users'].widget = forms.HiddenInput()



class OrcidImportGrantResultForm(forms.Form):
    title = forms.CharField(max_length=1024, disabled=True)
    grant_number = forms.CharField(
        max_length=30, disabled=True)
    total_amount_awarded = forms.FloatField(disabled=True)
    amount_awarded_currency = forms.CharField(max_length=3, disabled=True)
    role = forms.MultipleChoiceField(choices=Grant.ROLE_CHOICES, initial="PI")
    grant_pi_full_name=forms.CharField(max_length=255, required=False)
    grant_start = forms.CharField(max_length=150, disabled=True)
    grant_end = forms.CharField(max_length=150, disabled=True)
    funding_agency = forms.CharField(max_length=1024, disabled=True)
    percent_credit = forms.FloatField(max_value=100, min_value=0, required=False, initial=0)
    direct_funding = forms.FloatField(required=False, initial=0)
    STATUS_CHOICES = (
        ('Active', 'Active'),
        ('Archived', 'Archived'),
        ('Pending', 'Pending'),
    )
    status = forms.MultipleChoiceField(choices=STATUS_CHOICES, initial='Active')
    unique_id = forms.CharField(max_length=255, disabled=True)
    source_pk = forms.IntegerField(widget=forms.HiddenInput(), disabled=True, required=False)
    selected = forms.BooleanField(initial=False, required=False)

class GrantDeleteForm(forms.Form):
    title = forms.CharField(max_length=255, disabled=True)
    grant_number = forms.CharField(
        max_length=30, required=False, disabled=True)
    grant_end = forms.CharField(max_length=150, required=False, disabled=True)
    selected = forms.BooleanField(initial=False, required=False)


class GrantDownloadForm(forms.Form):
    pk = forms.IntegerField(required=False, disabled=True)
    title = forms.CharField(required=False, disabled=True)
    project_pk = forms.IntegerField(required=False, disabled=True)
    pi_first_name = forms.CharField(required=False, disabled=True)
    pi_last_name = forms.CharField(required=False, disabled=True)
    role = forms.CharField(required=False, disabled=True)
    grant_pi = forms.CharField(required=False, disabled=True)
    total_amount_awarded = forms.FloatField(required=False, disabled=True)
    funding_agency = forms.CharField(required=False, disabled=True)
    grant_number = forms.CharField(required=False, disabled=True)
    grant_start = forms.DateField(required=False, disabled=True)
    grant_end = forms.DateField(required=False, disabled=True)
    percent_credit = forms.FloatField(required=False, disabled=True)
    direct_funding = forms.FloatField(required=False, disabled=True)
    selected = forms.BooleanField(initial=False, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['pk'].widget = forms.HiddenInput()
