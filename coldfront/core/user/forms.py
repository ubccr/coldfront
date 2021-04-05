from datetime import datetime

from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.utils.html import mark_safe

from coldfront.core.user.utils import send_account_activation_email
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


class UserRegistrationForm(UserCreationForm):

    email = forms.EmailField(label='Email Address', widget=forms.EmailInput())
    first_name = forms.CharField(label='First Name')
    middle_name = forms.CharField(label='Middle Name', required=False)
    last_name = forms.CharField(label='Last Name')
    password1 = forms.CharField(
        label='Enter Password', widget=forms.PasswordInput())
    password2 = forms.CharField(
        label='Confirm Password', widget=forms.PasswordInput())

    def __init__(self, *args, **kwargs):
        self.middle_name = ''
        super().__init__(*args, **kwargs)

    def clean_email(self):
        cleaned_data = super().clean()
        email = cleaned_data['email'].lower()
        if (User.objects.filter(username=email).exists() or
                User.objects.filter(email=email).exists()):
            raise forms.ValidationError(
                'A user with that email address already exists.')
        return email

    def clean_middle_name(self):
        cleaned_data = super().clean()
        self.middle_name = cleaned_data.pop('middle_name', '')
        return cleaned_data

    def save(self, commit=True):
        model = super().save(commit=False)
        model.username = model.email
        model.is_active = False
        if commit:
            model.save()
        model.refresh_from_db()
        model.userprofile.middle_name = self.middle_name
        model.userprofile.save()
        return model

    class Meta:
        model = User
        fields = (
            'email', 'first_name', 'middle_name', 'last_name', 'password1',
            'password2',)


class UserLoginForm(AuthenticationForm):

    def clean_username(self):
        cleaned_data = super().clean()
        return cleaned_data.get('username').lower()

    def confirm_login_allowed(self, user):
        if not user.is_active:
            send_account_activation_email(user)
            raise forms.ValidationError(
                'Your account has been created, but is inactive. Please click '
                'the link sent to your email address to activate your '
                'account.', code='inactive')


class UserProfileUpdateForm(forms.Form):
    first_name = forms.CharField(label='First Name')
    middle_name = forms.CharField(label='Middle Name', required=False)
    last_name = forms.CharField(label='Last Name')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


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
