from django import forms


class ResourceSearchForm(forms.Form):
    """ Search form for the Resource list page.
    """
    model = forms.CharField(
        label='Model', max_length=100, required=False)
    serialNumber = forms.CharField(
        label='Serial Number', max_length=100, required=False)
    vendor = forms.CharField(
        label='Vendor', max_length=100, required=False)
    installDate = forms.DateField(
        label='Install Date',
        widget=forms.DateInput(attrs={'class': 'datepicker'}),
        required=False)
    serviceStart = forms.DateField(
        label='Service Start',
        widget=forms.DateInput(attrs={'class': 'datepicker'}),
        required=False)
    serviceEnd =  forms.DateField(
        label='Service End', 
        widget=forms.DateInput(attrs={'class': 'datepicker'}), 
        required=False)
    warrantyExpirationDate = forms.DateField(
        label='Warranty Expiration Date', 
        widget=forms.DateInput(attrs={'class': 'datepicker'}),
        required=False)
    show_allocatable_resources = forms.BooleanField(initial=False, required=False)


class ResourceAttributeDeleteForm(forms.Form):
    pk = forms.IntegerField(required=False, disabled=True)
    name = forms.CharField(max_length=150, required=False, disabled=True)
    value = forms.CharField(max_length=150, required=False, disabled=True)
    selected = forms.BooleanField(initial=False, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['pk'].widget = forms.HiddenInput()