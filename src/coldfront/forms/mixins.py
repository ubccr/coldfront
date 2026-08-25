# SPDX-FileCopyrightText: (C) DigitalOcean, LLC
# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

import logging
import time

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout
from django import forms
from django.core.validators import EMPTY_VALUES
from django.db import models as dj_models
from django.db.models import Q
from django.utils.translation import gettext as _

from coldfront.core.choices import CustomFieldUIEditableChoices
from coldfront.core.models import CustomField, ObjectType, SavedFilter, Tag
from coldfront.forms.fields import DynamicModelMultipleChoiceField
from coldfront.registry import get_allocation_extensions
from coldfront.users.permissions import get_permission_for_model

logger = logging.getLogger(__name__)


class AllocationExtensionFormMixin:
    """
    Mixin for forms that need dynamic fields for allocation extensions.

    Adds form fields for each ``requestable_fields`` on every extension
    registered for the allocation's resource.  Stores field-to-extension
    mapping in ``self._extension_field_map`` for use in save logic.

    In ``form_mode="change"`` (allocation change request forms), also adds
    fields for each ``changeable_fields`` token, including related-object
    markers (``$related:<fk>.<field>``) which surface fields on the FK target.

    Usage:
        class MyForm(AllocationExtensionFormMixin, PrimaryModelForm):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self._build_extension_fields()
    """

    # "request" builds requestable fields only; "change" also builds
    # changeable fields (scalar + related-object markers).
    form_mode = "request"

    def __init__(self, *args, **kwargs):
        self._extension_field_map = []
        super().__init__(*args, **kwargs)

    def _get_allocation(self):
        """
        Resolve the allocation from the form instance or POST data.
        Override on forms where the allocation is determined differently.
        """
        if self.instance and self.instance.pk:
            return getattr(self.instance, "allocation", None)
        return None

    def _get_resource_model_path(self, allocation):
        """
        Return the dotted model path of the allocation's resource object.
        """
        if allocation is None:
            return None
        resource = allocation.resource_object
        if resource is None:
            return None
        return resource._meta.label_lower

    def _build_extension_fields(self, allocation=None):
        """
        Add form fields for each extension's ``requestable_fields``.

        Stores the field mapping in ``self._extension_field_map`` for use
        by ``_collect_extension_data()`` and ``save()``.
        """
        self._extension_field_map = []

        resource_path = self._get_resource_model_path(allocation)
        if not resource_path:
            return

        for model in get_allocation_extensions(resource_path):
            if model is None:
                continue

            tokens = model.fields_for_change() if self.form_mode == "change" else model.requestable_fields()
            if not tokens:
                continue

            # Fetch the current extension instance for pre-filling
            extension_instance = None
            if allocation and allocation.pk:
                # Resolve the reverse accessor name for the allocation FK
                related_name = None
                try:
                    allocation_field = model._meta.get_field("allocation")
                    related_name = allocation_field.remote_field.related_name
                except (AttributeError, ValueError):
                    logger.warning(
                        "Could not resolve the allocation reverse accessor for extension %s: pre-fill will be skipped.",
                        model.__qualname__,
                    )
                if not related_name:
                    related_name = f"{model._meta.model_name}_set"
                try:
                    extension_instance = getattr(allocation, related_name).first()
                except (AttributeError, ValueError):
                    logger.warning(
                        "Could not fetch the current extension instance for %s via %r: pre-fill will be skipped.",
                        model.__qualname__,
                        related_name,
                    )

            field_names = []
            related_fields = []
            for token in tokens:
                if model.is_related_field_token(token):
                    fk_name, target_field = model.parse_related_field_token(token)

                    # Resolve the FK field and its target model
                    fk = next((f for f in model._meta.local_fields if f.name == fk_name), None)
                    if fk is None or not isinstance(fk, dj_models.ForeignKey):
                        logger.error(
                            "Related-object token '$related:%s.%s' on %s does not "
                            "resolve to a ForeignKey named '%s': field will be skipped.",
                            fk_name,
                            target_field,
                            model.__qualname__,
                            fk_name,
                        )
                        continue
                    target_model = fk.remote_field.model
                    target_model_field = next(
                        (f for f in target_model._meta.local_fields if f.name == target_field), None
                    )
                    if target_model_field is None:
                        logger.error(
                            "Related-object token '$related:%s.%s' on %s references "
                            "field '%s' on %s which does not exist: field will be skipped.",
                            fk_name,
                            target_field,
                            model.__qualname__,
                            target_field,
                            target_model.__qualname__,
                        )
                        continue

                    target_instance = getattr(extension_instance, fk_name) if extension_instance is not None else None
                    form_field = self._form_field_for_model_field(target_model_field, target_instance)
                    if form_field is not None:
                        if target_instance is None:
                            # No related object is linked yet — disable the field
                            # and explain, so the change can't be silently dropped.
                            form_field.disabled = True
                            fk_label = str(model._meta.get_field(fk_name).verbose_name).capitalize()
                            field_label = str(target_model_field.verbose_name).capitalize()
                            form_field.help_text = _(
                                "No {fk} is linked to this allocation yet — {field} cannot be changed until one is set."
                            ).format(fk=fk_label, field=field_label)
                        form_field_name = f"rel_{target_model._meta.model_name}_{target_field}"
                        self.fields[form_field_name] = form_field
                        related_fields.append(
                            {
                                "fk_name": fk_name,
                                "target_field": target_field,
                                "target_model": target_model,
                                "form_field_name": form_field_name,
                            }
                        )
                    continue

                # Scalar requestable/changeable field on the extension model
                model_field = next((f for f in model._meta.local_fields if f.name == token), None)
                if model_field is None:
                    logger.error(
                        "Extension field '%s' on %s does not exist: field will be skipped.",
                        token,
                        model.__qualname__,
                    )
                    continue
                form_field = self._form_field_for_model_field(model_field, extension_instance)
                if form_field is not None:
                    self.fields[f"ext_{model._meta.model_name}_{token}"] = form_field
                    field_names.append(token)

            if field_names or related_fields:
                self._extension_field_map.append(
                    {
                        "model_path": f"{model._meta.app_label}.{model._meta.model_name}",
                        "model": model,
                        "field_names": field_names,
                        "related_fields": related_fields,
                    }
                )

    def _form_field_for_model_field(self, model_field, extension_instance=None):
        """
        Build a Django form field from a model field definition.
        Pre-fills with the current extension instance value if available.

        Checks ``requestable_fields_overrides()`` on the extension model class
        first; if a custom field is registered for this field name, it is used
        instead of the auto-generated field.
        """
        from django.db import models as dj_models

        field_name = model_field.name

        # Check for a custom field override registered on the extension model
        extension_model_class = model_field.model
        if hasattr(extension_model_class, "requestable_fields_overrides"):
            overrides = extension_model_class.requestable_fields_overrides()
        else:
            overrides = {}
        if field_name in overrides:
            custom_field = overrides[field_name]
            if custom_field is not None:
                # Extension fields are always optional
                custom_field.required = False
                # Pre-fill with current value if available
                if extension_instance is not None:
                    current_value = getattr(extension_instance, field_name, None)
                    if current_value is not None:
                        custom_field.initial = current_value
                return custom_field
            return None  # Explicit None means skip this field

        current_value = None
        if extension_instance is not None:
            current_value = getattr(extension_instance, field_name, None)

        verbose_name = (
            str(model_field.verbose_name).capitalize() if hasattr(model_field, "verbose_name") else field_name
        )
        kwargs = {
            "label": verbose_name,
            "required": False,
            "initial": current_value,
        }

        if isinstance(model_field, (dj_models.PositiveBigIntegerField, dj_models.PositiveIntegerField)):
            return forms.IntegerField(**kwargs, min_value=0)
        elif isinstance(model_field, dj_models.IntegerField):
            return forms.IntegerField(**kwargs)
        elif isinstance(model_field, dj_models.DurationField):
            return forms.CharField(
                label=verbose_name,
                required=False,
                initial=str(current_value) if current_value else None,
                help_text=_("Duration (e.g. 3:00:00 or 3 days, 0:00:00)"),
            )
        elif isinstance(model_field, dj_models.BooleanField):
            return forms.BooleanField(**kwargs)
        elif isinstance(model_field, dj_models.CharField):
            return forms.CharField(**kwargs)
        else:
            return None

    def _collect_extension_data(self):
        """
        Return a dict mapping extension model paths (strings) to dicts of
        cleaned field values collected from the form.

        Called in ``_post_clean`` or ``save`` to gather extension values.
        Scalar fields map to the extension path; related-object markers map to
        ``<extension path>.<fk>`` with values keyed by the target field name.
        """
        result = {}
        for entry in self._extension_field_map:
            path = entry["model_path"]
            model_name = entry["model"]._meta.model_name

            # Scalar extension fields
            values = {}
            for field_name in entry["field_names"]:
                value = self.cleaned_data.get(f"ext_{model_name}_{field_name}")
                if value not in EMPTY_VALUES:
                    values[field_name] = value
            if values:
                result[path] = values

            # Related-object fields (change requests only)
            for rel in entry["related_fields"]:
                value = self.cleaned_data.get(rel["form_field_name"])
                if value not in EMPTY_VALUES:
                    rdict = result.setdefault(f"{path}.{rel['fk_name']}", {})
                    rdict[rel["target_field"]] = value
        return result


class HorizontalFormMixin:
    """
    Mixin for horizontal form layouts with crispy
    """

    @property
    def helper(self):
        """
        crispy forms helper which defines the form rendering behavior.
        """
        helper = FormHelper()
        helper.form_tag = False
        helper.form_class = "form-horizontal"
        helper.label_class = "col-lg-3 text-end"
        helper.field_class = "col-lg-6"
        helper.layout = self.get_layout()
        return helper

    def get_layout(self):
        """
        The crispy layout for the form. Sub-classes can override for custom layout
        """
        return Layout(*self.fieldsets)


class TagsMixin(forms.Form):
    """
    Mixin for forms that support tagging.

    Provides a field for selecting tags,
    with options limited to those applicable to the form's model.
    """

    tags = forms.ModelMultipleChoiceField(
        queryset=Tag.objects.all(),
        required=False,
        label=_("Tags"),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Limit tags to those applicable to the object type
        object_type = ObjectType.objects.get_for_model(self._meta.model)
        self.fields["tags"].queryset = self.fields["tags"].queryset.filter(
            Q(object_types__id=object_type.pk) | Q(object_types__isnull=True)
        )


class SavedFiltersMixin(forms.Form):
    """
    Form mixin for forms that support saved filters.

    Provides a field for selecting a saved filter,
    with options limited to those applicable to the form's model.
    """

    filter_id = DynamicModelMultipleChoiceField(
        queryset=SavedFilter.objects.all(),
        required=False,
        label=_("Saved Filter"),
        query_params={
            "usable": True,
        },
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Limit saved filters to those applicable to the form's model
        if hasattr(self, "model"):
            object_type = ObjectType.objects.get_for_model(self.model)
            self.fields["filter_id"].widget.add_query_params(
                {
                    "object_type_id": object_type.pk,
                }
            )


class ChangelogMessageMixin(forms.Form):
    """
    Adds an optional field for recording a message on the resulting changelog record(s).
    """

    changelog_message = forms.CharField(
        required=False,
        max_length=200,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Declare changelog_message a meta field
        if hasattr(self, "meta_fields"):
            self.meta_fields.append("changelog_message")
        else:
            self.meta_fields = ["changelog_message"]


class CheckLastUpdatedMixin(forms.Form):
    """
    Checks whether the object being saved has been updated since the form was initialized. If so, validation fails.
    This prevents a user from inadvertently overwriting any changes made to the object between when the form was
    initialized and when it was submitted.

    This validation does not apply to newly created objects, or if the `_init_time` field is not present in the form
    data.
    """

    _init_time = forms.DecimalField(initial=time.time, required=False, widget=forms.HiddenInput())

    def clean(self):
        super().clean()

        # Skip for absent or newly created instances
        if not self.instance or not self.instance.pk:
            return

        # Skip if a form init time has not been specified
        if not (form_init_time := self.cleaned_data.get("_init_time")):
            return

        # Skip if the object does not have a last_updated value
        if not (last_updated := getattr(self.instance, "last_updated", None)):
            return

        # Check that the submitted initialization time is not earlier than the object's modification time
        if form_init_time < last_updated.timestamp():
            raise forms.ValidationError(
                _(
                    "This object has been modified since the form was rendered. Please consult the object's change "
                    "log for details."
                )
            )


class CustomFieldsMixin:
    """
    Extend a Form to include custom field support.

    Attributes:
        model: The model class
    """

    model = None

    def __init__(self, *args, **kwargs):
        self.custom_fields = {}
        self.custom_field_groups = {}

        super().__init__(*args, **kwargs)

        self._append_customfield_fields()

    def _get_content_type(self):
        """
        Return the ObjectType of the form's model.
        """
        if not getattr(self, "model", None):
            raise NotImplementedError(
                _("{class_name} must specify a model class.").format(class_name=self.__class__.__name__)
            )
        return ObjectType.objects.get_for_model(self.model)

    def _get_custom_fields(self, content_type):
        fields = []

        for cf in CustomField.objects.get_for_model(content_type.model_class()):
            # Return only custom fields that are not hidden from the UI
            if cf.ui_editable == CustomFieldUIEditableChoices.HIDDEN:
                continue

            if cf.required_action:
                if not hasattr(self, "user"):
                    continue

                # Return custom fields only if the user has been granted the required action
                perm = get_permission_for_model(content_type.model_class(), cf.required_action)
                if not self.user.has_perms([perm]):
                    continue

            fields.append(cf)

        return fields

    def _get_form_field(self, customfield):
        return customfield.to_form_field()

    def _append_customfield_fields(self):
        """
        Append form fields for all CustomFields assigned to this object type.
        """
        for customfield in self._get_custom_fields(self._get_content_type()):
            field_name = f"cf_{customfield.name}"
            self.fields[field_name] = self._get_form_field(customfield)

            # Annotate the field in the list of CustomField form fields
            self.custom_fields[field_name] = customfield
            if customfield.group_name not in self.custom_field_groups:
                self.custom_field_groups[customfield.group_name] = []
            self.custom_field_groups[customfield.group_name].append(field_name)
