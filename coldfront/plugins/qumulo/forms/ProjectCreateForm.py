from django import forms
from coldfront.core.field_of_science.models import FieldOfScience
from coldfront.plugins.qumulo.validators import validate_single_ad_user_skip_admin


class ProjectCreateForm(forms.Form):
    def __init__(self, *args, **kwargs):
        self.user_id = kwargs.pop("user_id")
        super().__init__(*args, **kwargs)
        self.fields["pi"].initial = self.user_id
        self.fields["field_of_science"].choices = self.get_fos_choices()
        self.fields["field_of_science"].initial = FieldOfScience.DEFAULT_PK

    title = forms.CharField(
        label="Title",
        max_length=255,
    )
    pi = forms.CharField(
        label="Principal Investigator",
        max_length=128,
        validators=[validate_single_ad_user_skip_admin],
    )
    description = forms.CharField(
        required=False,
        widget=forms.Textarea,
    )
    field_of_science = forms.ChoiceField(label="Field of Science")

    def get_fos_choices(self):
        return map(lambda fos: (fos.id, fos.description), FieldOfScience.objects.all())
