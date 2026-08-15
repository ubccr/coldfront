# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from crispy_forms.layout import Fieldset, Layout
from django import forms
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.core.validators import EMPTY_VALUES
from django.utils.translation import gettext_lazy as _

from coldfront.core.choices import CommentKindChoices
from coldfront.core.models import CommentEntry, ObjectType
from coldfront.forms import (
    PrimaryModelForm,
    PrimaryModelImportForm,
    TenancyForm,
    TenancyImportForm,
)
from coldfront.forms.fields import (
    CommentField,
    CSVContentTypeObjectField,
    CSVModelChoiceField,
    DynamicModelChoiceField,
)
from coldfront.forms.layouts import DateTime
from coldfront.forms.mixins import AllocationExtensionFormMixin, HorizontalFormMixin
from coldfront.forms.widgets import HTMXSelectWidget
from coldfront.ras.choices import get_resource_object_choices
from coldfront.ras.models import Allocation, Project
from coldfront.users.models import User
from coldfront.users.permissions import get_permission_for_model
from coldfront.utils.forms import get_field_value
from coldfront.utils.jsonschema import JSONSchemaProperty


class AllocationBaseForm(AllocationExtensionFormMixin, PrimaryModelForm):
    resource_object = forms.ChoiceField(
        choices=[],
        label=_("Resource"),
        widget=HTMXSelectWidget(),
        help_text=_("Select a resources for this allocation request"),
    )

    class Meta:
        abstract = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["resource_object"].choices = get_resource_object_choices(self.user)

        # Set initial value for resource_object when editing an existing instance
        if self.instance and self.instance.pk and self.instance.resource_object:
            ct = ContentType.objects.get_for_model(self.instance.resource_object)
            value = f"{ct.id}:{self.instance.resource_object_id}"
            self.fields["resource_object"].initial = value

        # Track resource-specific allocation attribute fields
        self.attr_fields = []

        # Extend form with fields for allocation attributes
        for attr, form_field in self._get_attr_form_fields().items():
            field_name = f"attr_{attr}"
            self.attr_fields.append(field_name)
            self.fields[field_name] = form_field
            if self.instance.attribute_data:
                self.fields[field_name].initial = self.instance.attribute_data.get(attr)

        # Build extension fields from the selected resource
        # For existing allocations, use the instance; for new allocations,
        # derive the resource from POST/initial data (HTMX-driven)
        allocation = self.instance if self.instance.pk else None
        if allocation is None:
            allocation = self._resolve_allocation_from_resource_object()
        self._build_extension_fields(allocation)

    def _resolve_allocation_from_resource_object(self):
        """
        Derive a minimal allocation-like object from the resource_object field
        so extension fields can be built even before the allocation is saved.

        Uses POST data or the field's initial value to resolve the resource.
        Returns an Allocation instance with only resource_object set, or None.
        """
        ro = get_field_value(self, "resource_object")
        if not ro:
            return None
        try:
            ct_id, object_id = ro.split(":")
            ct = ContentType.objects.get(pk=int(ct_id))
            ct.get_object_for_this_type(pk=int(object_id))
            # Create a temporary allocation with resource_object fields set
            from coldfront.ras.models import Allocation

            alloc = Allocation(
                resource_object_type=ct,
                resource_object_id=int(object_id),
            )
            return alloc
        except (ValueError, ContentType.DoesNotExist, ObjectDoesNotExist, TypeError):
            return None

    def _get_schema(self):
        if ro := get_field_value(self, "resource_object"):
            try:
                ct_id, object_id = ro.split(":")
                ct = ContentType.objects.get(pk=ct_id)
                obj = ct.get_object_for_this_type(pk=object_id)
                if hasattr(obj, "schema"):
                    return obj.schema
            except (ValueError, ContentType.DoesNotExist, ObjectDoesNotExist):
                pass

        return None

    def clean_resource_object(self):
        data = self.cleaned_data["resource_object"]
        try:
            ct_id, object_id = data.split(":")
            ct = ContentType.objects.get(pk=ct_id)
            ct.get_object_for_this_type(pk=object_id)
        except (ValueError, ContentType.DoesNotExist, ObjectDoesNotExist):
            raise forms.ValidationError(_("Selected resource object does not exist."))
        return {"content_type": ct, "object_id": object_id}

    def _post_clean(self):
        resource_data = self.cleaned_data["resource_object"]
        self.instance.resource_object_type = resource_data["content_type"]
        self.instance.resource_object_id = resource_data["object_id"]

        # Compile attribute data from the individual form fields
        if resource_data:
            self.instance.attribute_data = {
                name[5:]: self.cleaned_data[name]  # Remove the attr_ prefix
                for name in self.attr_fields
                if self.cleaned_data.get(name) not in EMPTY_VALUES
            }

        # Collect extension data for creation after save
        self.instance._extension_create_data = self._collect_extension_data()

        return super()._post_clean()

    def _get_attr_form_fields(self):
        """
        Return a dictionary mapping of attribute names to form fields, suitable for extending
        the form per the selected resource object allocation attributes.
        """

        schema = self._get_schema()
        if not schema:
            return {}

        properties = schema.get("properties", {})
        required_fields = schema.get("required", [])

        attr_fields = {}
        for name, options in properties.items():
            prop = JSONSchemaProperty(**options)
            if prop.requiredAction:
                if not getattr(self, "user", None):
                    continue

                if not getattr(self._meta, "model", None):
                    continue

                content_type = ObjectType.objects.get_for_model(self._meta.model)
                perm = get_permission_for_model(content_type.model_class(), prop.requiredAction)
                if not self.user.has_perms([perm]):
                    continue

            attr_fields[name] = prop.to_form_field(name, required=name in required_fields)

        return dict(sorted(attr_fields.items()))


class AllocationRequestForm(AllocationBaseForm):
    project = forms.ModelChoiceField(
        label=_("Project"),
        queryset=Project.objects.all(),
        required=False,
        disabled=True,
        widget=forms.HiddenInput(),
    )
    justification = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 5}),
        help_text=_(
            "Please provide the justification for how you intend to use the resource"
            " to further the research goals of your project"
        ),
    )

    class Meta:
        model = Allocation
        fields = [
            "project",
            "justification",
        ]

    def save(self, commit=True):
        instance = super().save(commit=False)
        if commit:
            instance.save()
            # Create extension instances from collected data
            self._create_extensions(instance)
        return instance

    def _create_extensions(self, allocation):
        """Create extension instances for the allocation."""
        extension_data = getattr(allocation, "_extension_create_data", {}) or {}
        if not extension_data:
            return

        # Build a lookup from path → model class from _extension_field_map
        path_to_model = {e["model_path"]: e["model"] for e in self._extension_field_map}

        for ext_path, values in extension_data.items():
            model = path_to_model.get(ext_path)
            if model is not None:
                model.create_for_allocation(allocation, values=values)

    @property
    def fieldsets(self):
        fieldsets = [
            Fieldset(
                "Allocation Request",
                "project",
                "resource_object",
                *self.attr_fields,
                "justification",
            ),
        ]
        # Add extension fieldsets
        for entry in self._extension_field_map:
            header = _(f"{entry['model']._meta.verbose_name.title()} Details")
            field_names = [f"ext_{entry['model']._meta.model_name}_{fn}" for fn in entry["field_names"]]
            if field_names:
                fieldsets.append(Fieldset(header, *field_names))
        return fieldsets


class AllocationReviewForm(HorizontalFormMixin, forms.ModelForm):
    project = forms.ModelChoiceField(
        label=_("Project"),
        queryset=Project.objects.all(),
        required=False,
        disabled=True,
    )
    owner = forms.ModelChoiceField(
        queryset=User.objects.all(),
        label=_("Owner"),
        required=False,
        disabled=True,
    )
    comments = CommentField()

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

    class Meta:
        model = Allocation
        fields = [
            "project",
            "owner",
        ]

    @property
    def fieldsets(self):
        return [
            Layout(
                "project",
                "owner",
                "comments",
            ),
        ]

    def save(self, commit=True):
        instance = super().save(commit=False)
        if commit:
            instance.save()
            self._create_comment_entry()
        return instance

    def _create_comment_entry(self):
        comments = self.cleaned_data.get("comments")
        if comments:
            CommentEntry.objects.create(
                assigned_object=self.instance,
                created_by=getattr(self, "user", None),
                kind=CommentKindChoices.KIND_INFO,
                comments=comments,
            )


class AllocationForm(AllocationBaseForm, TenancyForm, PrimaryModelForm):
    project = DynamicModelChoiceField(
        label=_("Project"),
        queryset=Project.objects.all(),
        required=True,
    )
    owner = DynamicModelChoiceField(
        label=_("Owner"),
        queryset=User.objects.all(),
        required=True,
    )
    comments = CommentField()

    class Meta:
        model = Allocation
        fields = [
            "project",
            "owner",
            "slug",
            "start_date",
            "end_date",
            "status",
            "description",
            "justification",
            "tags",
            "tenant",
            "tenant_group",
        ]

    def save(self, commit=True):
        instance = super().save(commit=False)
        if commit:
            instance.save()
            self.save_m2m()
            self._create_comment_entry()
            # Create extension instances from collected data
            self._create_extensions(instance)
        return instance

    def _create_extensions(self, allocation):
        """Create extension instances for the allocation."""
        extension_data = getattr(allocation, "_extension_create_data", {}) or {}
        if not extension_data:
            return

        # Build a lookup from path → model class from _extension_field_map
        path_to_model = {e["model_path"]: e["model"] for e in self._extension_field_map}

        for ext_path, values in extension_data.items():
            model = path_to_model.get(ext_path)
            if model is not None:
                model.create_for_allocation(allocation, values=values)

    def _create_comment_entry(self):
        comments = self.cleaned_data.get("comments")
        if comments:
            CommentEntry.objects.create(
                assigned_object=self.instance,
                created_by=getattr(self, "user", None),
                kind=CommentKindChoices.KIND_INFO,
                comments=comments,
            )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Disable allocation status as this managed by the AlocationStatusFlow
        # self.fields["status"].widget.attrs["disabled"] = True
        # self.fields["status"].required = False
        # self.fields["status"].disabled = True

        # Only admins can modify slug
        if hasattr(self, "user") and self.user and self.user.is_authenticated and self.user.is_superuser:
            return

        self.fields["slug"].widget.attrs["disabled"] = "disabled"
        self.fields["slug"].required = False
        self.fields["slug"].disabled = True

    @property
    def fieldsets(self):
        fieldsets = [
            Fieldset(
                _("Resource"),
                "resource_object",
                *self.attr_fields,
            ),
            Fieldset(
                _("Allocation"),
                "slug",
                "status",
                "project",
                "owner",
                DateTime("start_date"),
                DateTime("end_date"),
                "description",
                "justification",
            ),
            Fieldset(
                _("Comments"),
                "comments",
            ),
        ]
        # Add extension fieldsets
        for entry in self._extension_field_map:
            header = _(f"{entry['model']._meta.verbose_name.title()} Details")
            field_names = [f"ext_{entry['model']._meta.model_name}_{fn}" for fn in entry["field_names"]]
            if field_names:
                fieldsets.append(Fieldset(header, *field_names))
        return fieldsets


class AllocationActivateForm(AllocationBaseForm, PrimaryModelForm):
    project = DynamicModelChoiceField(
        label=_("Project"),
        queryset=Project.objects.all(),
        required=True,
    )
    owner = DynamicModelChoiceField(
        label=_("Owner"),
        queryset=User.objects.all(),
        required=True,
    )
    comments = CommentField()

    class Meta:
        model = Allocation
        fields = [
            "project",
            "owner",
            "start_date",
            "end_date",
            "description",
            "justification",
        ]

    def save(self, commit=True):
        instance = super().save(commit=False)
        if commit:
            instance.save()
            self.save_m2m()
            self._create_comment_entry()
            # Create extension instances from collected data
            self._create_extensions(instance)
        return instance

    def _create_extensions(self, allocation):
        """Create extension instances for the allocation."""
        extension_data = getattr(allocation, "_extension_create_data", {}) or {}
        if not extension_data:
            return

        # Build a lookup from path → model class from _extension_field_map
        path_to_model = {e["model_path"]: e["model"] for e in self._extension_field_map}

        for ext_path, values in extension_data.items():
            model = path_to_model.get(ext_path)
            if model is not None:
                model.create_for_allocation(allocation, values=values)

    def _create_comment_entry(self):
        comments = self.cleaned_data.get("comments")
        if comments:
            CommentEntry.objects.create(
                assigned_object=self.instance,
                created_by=getattr(self, "user", None),
                kind=CommentKindChoices.KIND_INFO,
                comments=comments,
            )

    @property
    def fieldsets(self):
        fieldsets = [
            Fieldset(
                _("Resource"),
                "resource_object",
                *self.attr_fields,
            ),
            Fieldset(
                _("Allocation"),
                "project",
                "owner",
                DateTime("start_date"),
                DateTime("end_date"),
                "description",
                "justification",
            ),
            Fieldset(
                _("Comments"),
                "comments",
            ),
        ]
        # Add extension fieldsets
        for entry in self._extension_field_map:
            header = _(f"{entry['model']._meta.verbose_name.title()} Details")
            field_names = [f"ext_{entry['model']._meta.model_name}_{fn}" for fn in entry["field_names"]]
            if field_names:
                fieldsets.append(Fieldset(header, *field_names))
        return fieldsets


class AllocationImportForm(TenancyImportForm, PrimaryModelImportForm):
    attribute_data = forms.JSONField(
        label=_("Attributes"),
        required=False,
        help_text=_("Attribute values for the assigned allocation type, passed as a dictionary"),
    )

    owner = CSVModelChoiceField(
        label=_("Owner"),
        queryset=User.objects.all(),
        required=True,
        to_field_name="username",
        help_text=_("The owner of the allocation"),
        error_messages={
            "invalid_choice": _("User not found."),
        },
    )

    project = CSVModelChoiceField(
        label=_("Project"),
        queryset=Project.objects.all(),
        required=True,
        to_field_name="name",
        error_messages={
            "invalid_choice": _("Project not found."),
        },
    )

    resource_object = CSVContentTypeObjectField(
        label=_("Resource"),
        required=True,
        to_field_name="name",
        help_text=_("Resource in the format <app_label>.<model>:<name> (e.g. ras.resource:My Cluster)"),
        error_messages={
            "invalid_choice": _("Resource not found."),
        },
    )

    class Meta:
        model = Allocation
        # resource_object is handled explicitly by CSVContentTypeObjectField
        fields = [
            "project",
            "owner",
            "start_date",
            "end_date",
            "status",
            "description",
            "justification",
            "tags",
            "tenant",
        ]

    def clean(self):
        super().clean()

        # Attribute data may be included only if a resource object is specified
        if self.cleaned_data.get("attribute_data") and not self.cleaned_data.get("resource_object"):
            raise forms.ValidationError(
                _(f"{self._get_profile_field_name()} must be specified if attribute data is provided.")
            )

        # Default attribute_data to an empty dictionary if a resource object is specified (to enforce schema validation)
        if self.cleaned_data.get("resource_object") and not self.cleaned_data.get("attribute_data"):
            self.cleaned_data["attribute_data"] = {}

    def save(self, commit=True):
        instance = super().save(commit=False)

        # Map the resolved resource_object to the GenericForeignKey fields
        resource_obj = self.cleaned_data.get("resource_object")
        if resource_obj:
            instance.resource_object_type = ContentType.objects.get_for_model(resource_obj)
            instance.resource_object_id = resource_obj.pk

        if commit:
            instance.save()
            self.save_m2m()
        return instance
