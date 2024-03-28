from django import forms
from django.db.models.functions import Lower
from django.shortcuts import get_object_or_404

from coldfront.core.allocation.models import (Allocation, AllocationAccount,
                                              AllocationAttributeType,
                                              AllocationAttribute,
                                              AllocationStatusChoice,
                                              AllocationNoteTags,
                                              AllocationUserNote)
from coldfront.core.allocation.utils import get_user_resources
from coldfront.core.note.models import NoteTags
from coldfront.core.project.models import Project
from coldfront.core.resource.models import Resource, ResourceType
from coldfront.core.utils.common import import_from_settings


class NoteCreateForm(forms.Form):
    
    title = forms.CharField(max_length=150)
    tags = forms.ModelChoiceField(
        queryset=NoteTags.objects.all(), empty_label=None) 
    message = forms.CharField(widget=forms.Textarea)
    note_to = forms.MultipleChoiceField(
        widget=forms.CheckboxSelectMultiple(attrs={'checked': 'checked'}), required=False)


    def __init__(self, pk,  *args, **kwargs):
        super().__init__(*args, **kwargs)
        allocation_obj = get_object_or_404(Allocation, pk=pk)
        user_query_set = allocation_obj.project.projectuser_set.select_related('user').filter(
            status__name__in=['Active', ]).order_by("user__username")
        user_query_set = user_query_set.exclude(user=allocation_obj.project.pi)
        if user_query_set:
            self.fields['note_to'].choices = ((user.user.username, "%s %s (%s)" % (
                user.user.first_name, user.user.last_name, user.user.username)) for user in user_query_set)
            self.fields['note_to'].help_text = '<br/>Select users in your project to send this note to. Only they can view this note'
        else:

            self.fields['note_to'].widget = forms.HiddenInput()
