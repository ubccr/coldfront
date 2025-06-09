from django import forms


class HelpForm(forms.Form):
    queue_email = forms.CharField(max_length=30, widget=forms.HiddenInput)
    first_name = forms.CharField(max_length=30)
    last_name = forms.CharField(max_length=30)
    user_email = forms.EmailField()
    subject = forms.CharField(max_length=50)
    message = forms.CharField(widget=forms.Textarea)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        initial = kwargs.get("initial")
        if initial.get("first_name"):
            self.fields["first_name"].widget = forms.HiddenInput()
        if initial.get("last_name"):
            self.fields["last_name"].widget = forms.HiddenInput()
        if initial.get("user_email"):
            self.fields["user_email"].widget = forms.HiddenInput()
