from django import forms

from coldfront.core.publication.models import PublicationSource
from django.shortcuts import get_object_or_404
from coldfront.core.project.models import Project
from coldfront.core.utils.common import import_from_settings

PLUGIN_ORCID = import_from_settings('PLUGIN_ORCID', False)
if PLUGIN_ORCID:
    ORCID_SANDBOX = import_from_settings('ORCID_SANDBOX', True)

class PublicationAddForm(forms.Form):
    title = forms.CharField(max_length=1024, required=True)
    author = forms.CharField(max_length=1024, required=True)
    year = forms.IntegerField(min_value=1500, max_value=2090, required=True)
    journal = forms.CharField(max_length=1024, required=True)
    source = forms.CharField(widget=forms.HiddenInput())  # initialized by view


class PublicationIdentifierSearchForm(forms.Form):
    search_id = forms.CharField(
        label='Search DOI', widget=forms.Textarea, required=False)


class PublicationORCIDSearchForm(forms.Form):
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
            self.fields['users'].help_text = '<br/>Select users in your project to pull their ORCID works information.'
        else:
            self.fields['users'].widget = forms.HiddenInput()
    
    

class PublicationResultForm(forms.Form):
    title = forms.CharField(max_length=1024, disabled=True)
    author = forms.CharField(disabled=True)
    year = forms.CharField(max_length=4, disabled=True)
    journal = forms.CharField(max_length=1024, disabled=True)
    unique_id = forms.CharField(max_length=255, disabled=True)
    source_pk = forms.IntegerField(widget=forms.HiddenInput(), disabled=True)
    selected = forms.BooleanField(initial=False, required=False)


class PublicationDeleteForm(forms.Form):
    title = forms.CharField(max_length=255, disabled=True)
    year = forms.CharField(max_length=30, disabled=True)
    selected = forms.BooleanField(initial=False, required=False)


class PublicationExportForm(forms.Form):
    title = forms.CharField(max_length=255, disabled=True)
    year = forms.CharField(max_length=30, disabled=True)
    unique_id = forms.CharField(max_length=255, disabled=True)
    selected = forms.BooleanField(initial=False, required=False)
