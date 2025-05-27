from django import forms


class AllocationMoveForm(forms.Form):
    destination_project = forms.IntegerField()
