from django import forms


class ProjectRemoveUserForm(forms.Form):
    username = forms.CharField(max_length=150, disabled=True)
    first_name = forms.CharField(max_length=30, required=False, disabled=True)
    last_name = forms.CharField(max_length=150, required=False, disabled=True)
    email = forms.EmailField(max_length=100, required=False, disabled=True)
    role = forms.CharField(max_length=30, disabled=True)
    status = forms.CharField(max_length=50, required=False, disabled=True)
    selected = forms.BooleanField(initial=False, required=False)


class ProjectRemovalRequestSearchForm(forms.Form):
    project_name = forms.CharField(label='Project Name',
                                   max_length=100, required=False)
    username = forms.CharField(
        label='User Username', max_length=100, required=False)
    requester = forms.CharField(
        label='Requester Username', max_length=100, required=False)
    email = forms.CharField(label='User Email', max_length=100, required=False)
    show_all_requests = forms.BooleanField(initial=True, required=False)


class ProjectRemovalRequestUpdateStatusForm(forms.Form):

    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Processing', 'Processing'),
    ]

    status = forms.ChoiceField(
        label='Status', choices=STATUS_CHOICES, required=True,
        widget=forms.Select())


class ProjectRemovalRequestCompletionForm(forms.Form):
    STATUS_CHOICES = [
        ('Processing', 'Processing'),
        ('Complete', 'Complete')
    ]

    status = forms.ChoiceField(
        label='Status', choices=STATUS_CHOICES, required=True,
        widget=forms.Select())