from django import forms

from coldfront.plugins.announcements.models import AnnouncementCategoryChoice, AnnouncementMailingListChoice


class AnnouncementCreateForm(forms.Form):
    title = forms.CharField(max_length=100)
    body = forms.CharField(widget=forms.Textarea)
    categories = forms.ModelMultipleChoiceField(
        queryset=AnnouncementCategoryChoice.objects.all(),
        required=False
    )
    mailing_lists = forms.ModelMultipleChoiceField(
        queryset=AnnouncementMailingListChoice.objects.all(),
        required=False
    )
    details_url = forms.URLField(
        max_length=100, required=False, help_text='For links to external sources with more information'
    )
    pinned = forms.BooleanField(required=False)


class AnnouncementFilterForm(forms.Form):
    title = forms.CharField(max_length=100, required=False)
    categories = forms.ModelMultipleChoiceField(
        queryset=AnnouncementCategoryChoice.objects.all(),
        required=False
    )