import re

from typing import Any
from django import forms

from coldfront.core.project.models import Project
from coldfront.core.user.models import User
from coldfront.plugins.qumulo.fields import ADUserField, StorageFileSystemPathField
from coldfront.plugins.qumulo.validators import (
    validate_leading_forward_slash,
    validate_single_ad_user,
    validate_ticket,
    validate_storage_name,
    validate_prepaid_start_date,
)

from coldfront.plugins.qumulo.constants import (
    STORAGE_SERVICE_RATES,
    PROTOCOL_OPTIONS,
)

from coldfront.core.constants import BILLING_CYCLE_OPTIONS


class AllocationForm(forms.Form):
    def __init__(self, *args, **kwargs):
        self.user_id = kwargs.pop("user_id")
        super(forms.Form, self).__init__(*args, **kwargs)
        self.fields["project_pk"].choices = self.get_project_choices()

    class Media:
        js = ("allocation.js",)

    project_pk = forms.ChoiceField(label="Project")
    storage_name = forms.CharField(
        help_text="Name of the Allocation",
        label="Name",
        validators=[validate_storage_name],
    )
    cost_center = forms.CharField(
        help_text="The cost center for billing",
        label="Cost Center",
    )
    billing_exempt = forms.ChoiceField(
        help_text="Exempt the allocation from billing",
        label="Billing Exempt",
        choices=[("Yes", "Yes"), ("No", "No")],
        initial="No",
        widget=forms.RadioSelect,
        required=True,
    )
    department_number = forms.CharField(
        help_text="The department for billing",
        label="Department Number",
    )
    technical_contact = forms.CharField(
        help_text="Who should be contacted regarding technical details. Accepts one WUSTL key.",
        label="Technical Contact",
        validators=[validate_single_ad_user],
        required=False,
    )
    billing_contact = forms.CharField(
        help_text="Who should be contacted regarding billing details. Accepts a single WUSTL key.",
        label="Billing Contact",
        validators=[validate_single_ad_user],
        required=False,
    )
    billing_cycle = forms.ChoiceField(
        choices=BILLING_CYCLE_OPTIONS,
        initial="monthly",
        label="Billing Cycle Options",
        help_text="Choose one billing cycle option from the above list",
        required=True,
    )
    prepaid_time = forms.IntegerField(
        help_text="Prepaid Time in Months",
        label="Prepaid Time",
        required=False,
    )
    prepaid_billing_date = forms.DateField(
        help_text="Start Date Date of Prepaid Billing",
        label="Prepaid Billing Start Date",
        validators=[validate_prepaid_start_date],
        required=False,
    )
    service_rate = forms.ChoiceField(
        help_text="Service rate option for the Storage2 allocation",
        label="Service Rate",
        choices=STORAGE_SERVICE_RATES,
    )
    storage_quota = forms.IntegerField(
        min_value=0,
        max_value=2000,
        help_text="Size of the allocation quota in TB",
        label="Limit (TB)",
    )
    protocols = forms.MultipleChoiceField(
        widget=forms.CheckboxSelectMultiple(),
        choices=PROTOCOL_OPTIONS,
        label="Protocols",
        help_text="Choose protocols from the above list (or leave blank to configure no protocol)",
        initial=["smb"],
        required=False,
    )
    storage_filesystem_path = StorageFileSystemPathField(
        help_text="Path of the allocation resource",
        label="Filesystem Path",
    )
    storage_export_path = forms.CharField(
        help_text="Path of the allocation resource",
        label="Export Path",
        initial="",
        required=False,
        validators=[validate_leading_forward_slash],
    )
    storage_ticket = forms.CharField(
        help_text="Associated IT Service Desk Ticket",
        label="ITSD Ticket",
        validators=[validate_ticket],
    )
    rw_users = ADUserField(
        label="Read/Write Users",
        initial="",
    )
    ro_users = ADUserField(label="Read Only Users", initial="", required=False)

    def _upper(self, val: Any) -> Any:
        return val.upper() if isinstance(val, str) else val

    def _s3_allocation_name_explain(self, name: str):
        preStr = "name for allocation using S3 protocol"
        if not re.match(r"^[a-z0-9]{1}", name):
            return "{:s} must begin with a-z or 0-9".format(preStr)
        if not re.search(r"[a-z0-9]{1}$", name):
            return "{:s} must end with a-z or 0-9".format(preStr)
        if len(name) < 3 or len(name) > 63:
            return "{:s} must be between 3 and 63 characters in length".format(preStr)
        if re.search(r"[^a-z0-9\-\.]", name):
            return "{:s} contains invalid characters".format(preStr)
        return "{:s} has an unknown error".format(preStr)

    def _validate_s3_allocation_name(self, name: str):
        nameRe = re.compile(r"^[a-z0-9]{1}[a-z0-9\-\.]{1,61}[a-z0-9]{1}$")
        if not nameRe.match(name):
            self.add_error(
                "storage_name",
                "{:s}: {:s}".format(name, self._s3_allocation_name_explain(name)),
            )
        elif ".." in name:
            self.add_error(
                "storage_name",
                "{:s}: double periods (..) not allowed for S3 protocol".format(name),
            )
        elif re.match(r"^\d+\.\d+\.\d+\.\d+", name):
            self.add_error(
                "storage_name",
                "{:s}: S3 allocation must not be formatted as an IPV4 address".format(
                    name
                ),
            )
        elif re.match(r"^xn--", name):
            self.add_error(
                "storage_name",
                "{:s}: xn-- is an illegal prefix for S3 allocation".format(name),
            )
        elif re.match(r"^sthree-", name):
            self.add_error(
                "storage_name",
                "{:s}: sthree- is an illegal prefix for S3 allocation".format(name),
            )
        elif re.search(r"-s3alias$", name):
            self.add_error(
                "storage_name",
                "{:s}: -s3alias is an illegal suffix for S3 allocation".format(name),
            )
        elif re.search(r"--ol-s3$", name):
            self.add_error(
                "storage_name",
                "{:s}: --ol-s3 is an illegal suffix for S3 allocation".format(name),
            )

    def clean(self) -> dict[str, Any]:
        cleaned_data = super().clean()
        protocols = cleaned_data.get("protocols")
        storage_export_path = cleaned_data.get("storage_export_path")
        storage_ticket = self._upper(cleaned_data.get("storage_ticket", None))

        if "nfs" in protocols:
            if storage_export_path == "":
                self.add_error(
                    "storage_export_path",
                    "Export Path must be defined when using NFS protocol",
                )

        if storage_ticket is not None:
            if "ITSD-" not in storage_ticket and len(storage_ticket) > 0:
                self.cleaned_data["storage_ticket"] = "ITSD-{:s}".format(storage_ticket)
            else:
                self.cleaned_data["storage_ticket"] = storage_ticket

    def get_project_choices(self) -> list[str]:
        # jprew - NOTE: accesses to db collections should be consolidated to
        # single classes
        user = User.objects.get(id=self.user_id)

        if user.is_superuser or user.has_perm("project.can_view_all_projects"):
            projects = Project.objects.all()
        else:
            projects = Project.objects.filter(pi=self.user_id)

        return map(lambda project: (project.id, project.title), projects)
