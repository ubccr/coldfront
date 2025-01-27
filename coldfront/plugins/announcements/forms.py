from django import forms

from coldfront.plugins.announcements.models import AnnouncementCategoryChoice, AnnouncementMailingListChoice


class AnnouncementCreateForm(forms.Form):
    title = forms.CharField(max_length=100)
    body = forms.CharField(widget=forms.Textarea)
    categories = forms.ModelMultipleChoiceField(
        queryset=AnnouncementCategoryChoice.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False
    )
    mailing_lists = forms.ModelMultipleChoiceField(
        queryset=AnnouncementMailingListChoice.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False
    )


class AnnouncementFilterForm(forms.Form):
    categories = forms.ModelMultipleChoiceField(
        queryset=AnnouncementCategoryChoice.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False
    )