from django import forms
from django.core.exceptions import ValidationError

from coldfront.core.user.models import User

from coldfront.plugins.qumulo.validators import validate_single_ad_user


class PrincipalInvestigatorField(forms.CharField):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    def to_python(self, value):
        return User.objects.get_or_create(username=value)[0]

    def clean(self, value):
        try:
            validate_single_ad_user(value)
        except ValidationError as error:
            try:
                User.objects.get(username=value)
            except User.DoesNotExist:
                raise error
            
        return super().clean(value)
