from django import forms


class SecureDirManageUsersForm(forms.Form):
    username = forms.CharField(max_length=150, disabled=True)
    first_name = forms.CharField(max_length=30, required=False, disabled=True)
    last_name = forms.CharField(max_length=150, required=False, disabled=True)
    email = forms.EmailField(max_length=100, required=False, disabled=True)
    selected = forms.BooleanField(initial=False, required=False)


class SecureDirManageUsersSearchForm(forms.Form):
    project_name = forms.CharField(label='Project Name',
                                      max_length=100, required=False)
    resource_name = forms.CharField(label='Directory Name',
                                    max_length=100, required=False)
    username = forms.CharField(
        label='User Username', max_length=100, required=False)
    email = forms.CharField(label='User Email', max_length=100, required=False)
    show_all_requests = forms.BooleanField(initial=True, required=False)


class SecureDirManageUsersRequestUpdateStatusForm(forms.Form):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Processing', 'Processing'),
    ]

    status = forms.ChoiceField(
        label='Status', choices=STATUS_CHOICES, required=True,
        widget=forms.Select())


class SecureDirManageUsersRequestCompletionForm(forms.Form):
    STATUS_CHOICES = [
        ('Processing', 'Processing'),
        ('Complete', 'Complete')
    ]

    status = forms.ChoiceField(
        label='Status', choices=STATUS_CHOICES, required=True,
        widget=forms.Select())
