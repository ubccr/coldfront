from django import forms
from django.utils.html import mark_safe


class UserSearchForm(forms.Form):
    CHOICES = [('username_only', 'Exact Username Only'),
               # ('all_fields', mark_safe('All Fields <a href="#" data-toggle="popover" data-trigger="focus" data-content="This option will be ignored if multiple usernames are specified."><i class="fas fa-info-circle"></i></a>')),
               ('all_fields', mark_safe('All Fields <span class="text-secondary">This option will be ignored if multiple usernames are entered in the search user text area.</span>')),
               ]
    q = forms.CharField(label='Search String', min_length=2, widget=forms.Textarea(attrs={'rows': 4}),
                        help_text='Copy paste usernames separated by space or newline for multiple username searches!')
    search_by = forms.ChoiceField(choices=CHOICES, widget=forms.RadioSelect(), initial='username_only')


class UserSelectForm(forms.Form):
    SEARCH_OPTIONS = [
        ('ignore_case', "Ignore Case"), ('match_whole_word', "Match Whole Word"), ('regex', "Regex")
    ]
    SEARCH_CHOICES = [('username_only', 'Exact Username Only'),
        ('all_fields', mark_safe('All Fields <span class="text-secondary">This option will be ignored if multiple usernames are entered in the search user text area.</span>')),
    ]
    query = forms.CharField(label='Search Query', widget=forms.Textarea(attrs={'rows': 4}),
                help_text='Copy paste usernames separated by space or newline for multiple username searches!')
    search_options = forms.ChoiceField(choices=SEARCH_OPTIONS, widget=forms.CheckboxSelectMultiple())
    search_by = forms.ChoiceField(choices=SEARCH_CHOICES, widget=forms.RadioSelect(), initial='username_only')


class UserOrcidEditForm(forms.Form):
    orcid1 = forms.CharField(max_length=4, label="&nbsp;", initial=None, required=False)
    orcid2 = forms.CharField(max_length=4, label="-", initial=None, required=False)
    orcid3 = forms.CharField(max_length=4, label="-", initial=None, required=False)
    orcid4 = forms.CharField(max_length=4, label="-", initial=None, required=False)
    
