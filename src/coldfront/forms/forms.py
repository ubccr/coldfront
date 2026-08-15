# SPDX-FileCopyrightText: (C) DigitalOcean, LLC
# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

import csv
import json
from io import StringIO

import yaml
from crispy_forms.helper import FormHelper
from django import forms
from django.utils.translation import gettext as _

from coldfront.constants import CSV_DELIMITERS
from coldfront.core.choices import CSVDelimiterChoices, ImportFormatChoices, ImportMethodChoices
from coldfront.forms.fields import CSVModelChoiceField, DynamicModelChoiceField, QueryField
from coldfront.forms.mixins import ChangelogMessageMixin, HorizontalFormMixin
from coldfront.forms.utils import parse_csv
from coldfront.models.features import ChangeLoggingMixin
from coldfront.tenancy.models import Tenant, TenantGroup


class ConfirmationForm(forms.Form):
    """
    A generic confirmation form. The form is not valid unless the `confirm` field is checked.
    """

    return_url = forms.CharField(required=False, widget=forms.HiddenInput())
    confirm = forms.BooleanField(required=True, widget=forms.HiddenInput(), initial=True)


class DeleteForm(ConfirmationForm):
    """
    Confirm the deletion of an object, optionally providing a changelog message.
    """

    changelog_message = forms.CharField(required=False, max_length=200)

    def __init__(self, *args, instance=None, **kwargs):
        super().__init__(*args, **kwargs)

        # Hide the changelog_message filed if the model doesn't support change logging
        if instance is None or not issubclass(instance._meta.model, ChangeLoggingMixin):
            self.fields.pop("changelog_message")


class FilterForm(forms.Form):
    """
    Base Form class for FilterSet forms.
    """

    q = QueryField(required=False, label=_("Search"))


class TableConfigForm(forms.Form):
    """
    Form for configuring user's table preferences.
    """

    available_columns = forms.MultipleChoiceField(
        choices=[],
        required=False,
        widget=forms.SelectMultiple(attrs={"size": 10, "class": "form-select"}),
        label=_("Available Columns"),
    )
    columns = forms.MultipleChoiceField(
        choices=[],
        required=False,
        widget=forms.SelectMultiple(attrs={"size": 10, "class": "form-select select-all"}),
        label=_("Selected Columns"),
    )

    def __init__(self, table, *args, **kwargs):
        self.table = table

        super().__init__(*args, **kwargs)

        # Initialize columns field based on table attributes
        if table:
            self.fields["available_columns"].choices = table.available_columns
            self.fields["columns"].choices = table.selected_columns

    @property
    def table_name(self):
        return self.table.__class__.__name__


class BulkImportForm(HorizontalFormMixin, ChangelogMessageMixin, forms.Form):
    import_method = forms.ChoiceField(choices=ImportMethodChoices, required=False)
    data = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"class": "font-monospace"}),
        help_text=_("Enter object data in CSV, JSON or YAML format."),
    )
    upload_file = forms.FileField(label=_("Data file"), required=False)
    format = forms.ChoiceField(choices=ImportFormatChoices, initial=ImportFormatChoices.AUTO)
    csv_delimiter = forms.ChoiceField(
        choices=CSVDelimiterChoices,
        initial=CSVDelimiterChoices.AUTO,
        label=_("CSV delimiter"),
        help_text=_("The character which delimits CSV fields. Applies only to CSV format."),
        required=False,
    )

    data_field = "data"

    def clean(self):
        super().clean()

        # Determine import method
        import_method = self.cleaned_data.get("import_method") or ImportMethodChoices.DIRECT

        # Determine whether we're reading from form data or an uploaded file
        if self.cleaned_data["data"] and import_method != ImportMethodChoices.DIRECT:
            raise forms.ValidationError(_("Form data must be empty when uploading/selecting a file."))
        if import_method == ImportMethodChoices.UPLOAD:
            self.upload_file = "upload_file"
            file = self.files.get("upload_file")
            data = file.read().decode("utf-8-sig")
        else:
            data = self.cleaned_data["data"]

        # Determine the data format
        if self.cleaned_data["format"] == ImportFormatChoices.AUTO:
            if self.cleaned_data["csv_delimiter"] != CSVDelimiterChoices.AUTO:
                # Specifying the CSV delimiter implies CSV format
                format = ImportFormatChoices.CSV
            else:
                format = self._detect_format(data)
        else:
            format = self.cleaned_data["format"]

        # Process data according to the selected format
        if format == ImportFormatChoices.CSV:
            delimiter = self.cleaned_data.get("csv_delimiter", CSVDelimiterChoices.AUTO)
            self.cleaned_data["data"] = self._clean_csv(data, delimiter=delimiter)
        elif format == ImportFormatChoices.JSON:
            self.cleaned_data["data"] = self._clean_json(data)
        elif format == ImportFormatChoices.YAML:
            self.cleaned_data["data"] = self._clean_yaml(data)
        else:
            raise forms.ValidationError(_("Unknown data format: {format}").format(format=format))

    def _detect_format(self, data):
        """
        Attempt to automatically detect the format (CSV, JSON, or YAML) of the given data, or raise
        a ValidationError.
        """
        try:
            if data[0] in ("{", "["):
                return ImportFormatChoices.JSON
            if data.startswith("---") or data.startswith("- "):
                return ImportFormatChoices.YAML
            # Look for any of the CSV delimiters in the first line (ignoring the default 'auto' choice)
            first_line = data.split("\n", 1)[0]
            csv_delimiters = CSV_DELIMITERS.values()
            if any(x in first_line for x in csv_delimiters):
                return ImportFormatChoices.CSV
        except IndexError:
            pass
        raise forms.ValidationError({"format": _("Unable to detect data format. Please specify.")})

    def _clean_csv(self, data, delimiter=CSVDelimiterChoices.AUTO):
        """
        Clean CSV-formatted data. The first row will be treated as column headers.
        """
        # Determine the CSV dialect
        if delimiter == CSVDelimiterChoices.AUTO:
            # This uses a rough heuristic to detect the CSV dialect based on the presence of supported delimiting
            # characters. If the data is malformed, we'll fall back to the default Excel dialect.
            delimiters = "".join(CSV_DELIMITERS.values())
            try:
                dialect = csv.Sniffer().sniff(data.strip(), delimiters=delimiters)
            except csv.Error:
                dialect = csv.excel
        elif delimiter in (CSVDelimiterChoices.COMMA, CSVDelimiterChoices.SEMICOLON, CSVDelimiterChoices.PIPE):
            dialect = csv.excel
            dialect.delimiter = delimiter
        elif delimiter == CSVDelimiterChoices.TAB:
            dialect = csv.excel_tab
        else:
            raise forms.ValidationError(
                {
                    "csv_delimiter": _("Invalid CSV delimiter"),
                }
            )

        stream = StringIO(data.strip())
        reader = csv.reader(stream, dialect=dialect)
        headers, records = parse_csv(reader)

        # Set CSV headers for reference by the model form
        headers.pop("id", None)
        self._csv_headers = headers

        return records

    def _clean_json(self, data):
        """
        Clean JSON-formatted data. If only a single object is defined, it will be encapsulated as a list.
        """
        try:
            data = json.loads(data)
            # Accommodate for users entering single objects
            if type(data) is not list:
                data = [data]
            return data
        except json.decoder.JSONDecodeError as err:
            raise forms.ValidationError({self.data_field: f"Invalid JSON data: {err}"})

    def _clean_yaml(self, data):
        """
        Clean YAML-formatted data. Data must be either
          a) A single document comprising a list of dictionaries (each representing an object), or
          b) Multiple documents, separated with the '---' token
        """
        records = []
        try:
            for data in yaml.load_all(data, Loader=yaml.SafeLoader):
                if type(data) is list:
                    records.extend(data)
                elif type(data) is dict:
                    records.append(data)
                else:
                    raise forms.ValidationError(
                        {
                            self.data_field: _(
                                "Invalid YAML data. Data must be in the form of multiple documents, or a single document "
                                "comprising a list of dictionaries."
                            )
                        }
                    )
        except yaml.error.YAMLError as err:
            raise forms.ValidationError({self.data_field: f"Invalid YAML data: {err}"})

        return records


class BulkDeleteForm(ConfirmationForm):
    pk = forms.ModelMultipleChoiceField(
        queryset=None,
        widget=forms.MultipleHiddenInput,
    )
    changelog_message = forms.CharField(required=False, max_length=200)

    def __init__(self, model, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["pk"].queryset = model.objects.all()

        # Hide the changelog_message filed if the model doesn't support change logging
        if model is None or not issubclass(model, ChangeLoggingMixin):
            self.fields.pop("changelog_message")

    @property
    def helper(self):
        """
        crispy forms helper which defines the form rendering behavior.
        """
        helper = FormHelper()
        helper.form_class = "form-horizontal"
        helper.form_tag = False
        helper.label_class = "col-lg-3 text-end"
        helper.field_class = "col-lg-6"
        return helper


class TenancyForm(forms.Form):
    tenant_group = DynamicModelChoiceField(
        label=_("Tenant group"),
        queryset=TenantGroup.objects.all(),
        required=False,
        null_option="None",
        initial_params={"tenants": "$tenant"},
    )
    tenant = DynamicModelChoiceField(
        label=_("Tenant"),
        queryset=Tenant.objects.all(),
        required=False,
        quick_add=True,
        query_params={"group_id": "$tenant_group"},
    )


class TenancyImportForm(forms.Form):
    tenant = CSVModelChoiceField(
        label=_("Tenant"),
        queryset=Tenant.objects.all(),
        required=False,
        to_field_name="name",
        help_text=_("Assigned tenant"),
    )
