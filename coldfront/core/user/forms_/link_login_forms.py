from django import forms


class RequestLoginLinkForm(forms.Form):

    email = forms.EmailField()

    def clean_email(self):
        email = self.cleaned_data['email']
        return email.lower()
