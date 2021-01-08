from datetime import datetime

from django import forms
from django.utils.html import mark_safe

from coldfront.core.user.models import UserProfile


class UserSearchForm(forms.Form):
    CHOICES = [('username_only', 'Exact Username Only'),
               # ('all_fields', mark_safe('All Fields <a href="#" data-toggle="popover" data-trigger="focus" data-content="This option will be ignored if multiple usernames are specified."><i class="fas fa-info-circle"></i></a>')),
               ('all_fields', mark_safe('All Fields <span class="text-secondary">This option will be ignored if multiple usernames are entered in the search user text area.</span>')),
               ]
    q = forms.CharField(label='Search String', min_length=2, widget=forms.Textarea(attrs={'rows': 4}),
                        help_text='Copy paste usernames separated by space or newline for multiple username searches!')
    search_by = forms.ChoiceField(choices=CHOICES, widget=forms.RadioSelect(), initial='username_only')

    search_by.widget.attrs.update({'rows': 4})


class UserAccessAgreementForm(forms.Form):

    POP_QUIZ_CHOICES = [
        ('1', '1'),
        ('2', '2'),
        ('24', '24'),
        ('48', '48'),
    ]

    pop_quiz_answer = forms.ChoiceField(
        choices=POP_QUIZ_CHOICES,
        help_text=(
            'You run a job that uses 2 of the 24 cores of a savio2 node, for '
            '1 hour. How many SUs have you used?'),
        label='Service Unit usage pop quiz',
        required=True,
        widget=forms.RadioSelect())

    acknowledgement = forms.BooleanField(
        initial=False,
        help_text=(
            'I have read the UC Berkeley Policies and Procedures and '
            'understand my responsibilities in the use of BRC computing '
            'resources managed by the BRC Program.'),
        label='Acknowledge & Sign',
        required=True)

    class Meta:
        model = UserProfile
        fields = ('pop_quiz_answer', 'acknowledgement', )

    def clean_pop_quiz_answer(self):
        pop_quiz_answer = int(self.cleaned_data['pop_quiz_answer'])
        if pop_quiz_answer != 24:
            raise forms.ValidationError('Incorrect answer.')
        return pop_quiz_answer
