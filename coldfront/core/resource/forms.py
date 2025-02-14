from django import forms

from coldfront.core.resource.models import ResourceType, ResourceAttribute
from django.core.validators import MinValueValidator, MaxValueValidator

from django.db.models.functions import Lower
class ResourceSearchForm(forms.Form):
    """ Search form for the Resource list page.
    """
    resource_name = forms.CharField(label='Resource Name',
        max_length=100, required=False)
    resource_type = forms.ModelChoiceField(
        label='Resource Type',
        queryset=ResourceType.objects.all().order_by(Lower('name')),
        required=False)
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


class ResourceAttributeCreateForm(forms.ModelForm):
    class Meta:
        model = ResourceAttribute
        fields = '__all__'
    def __init__(self, *args, **kwargs):
        super(ResourceAttributeCreateForm, self).__init__(*args, **kwargs)
        self.fields['resource_attribute_type'].queryset = self.fields['resource_attribute_type'].queryset.order_by(Lower('name'))


class ResourceAllocationUpdateForm(forms.Form):
    allocation_pk = forms.IntegerField(required=False)
    project = forms.CharField(max_length=250, required=False, disabled=True)
    usage = forms.CharField(max_length=350, required=False, disabled=True)
    user_count = forms.IntegerField(required=False, disabled=True)
    rawshare = forms.IntegerField(required=False, validators=[MinValueValidator(0), MaxValueValidator(1410065399)])

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['allocation_pk'].widget = forms.HiddenInput()
