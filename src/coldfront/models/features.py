# SPDX-FileCopyrightText: (C) DigitalOcean, LLC
# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

import json
from collections import defaultdict
from functools import cached_property

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.core.validators import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _
from taggit.managers import TaggableManager

from coldfront.constants import CUSTOMFIELD_EMPTY_VALUES
from coldfront.core.choices import CustomFieldUIVisibleChoices, ObjectChangeActionChoices
from coldfront.core.models.change_logging import ObjectChange
from coldfront.core.utils import CustomFieldJSONEncoder, is_taggable
from coldfront.registry import register_model_feature, register_model_view
from coldfront.users.permissions import ModelAction, register_model_actions
from coldfront.utils.jsonschema import validate_schema
from coldfront.utils.serialization import serialize_object

from .deletion import DeleteMixin


class CommentingMixin(models.Model):
    """
    Enables support for object commenting. Adds a generic relation (`comments`)
    to ColdFront's CommentEntry model.
    """

    comments = GenericRelation(
        to="core.CommentEntry",
        object_id_field="assigned_object_id",
        content_type_field="assigned_object_type",
    )

    class Meta:
        abstract = True


class ChangeLoggingMixin(DeleteMixin, models.Model):
    """
    Provides change logging support for a model. Adds the `created` and `last_updated` fields.
    """

    created = models.DateTimeField(
        verbose_name=_("created"),
        auto_now_add=True,
        blank=True,
        null=True,
    )
    last_updated = models.DateTimeField(
        verbose_name=_("last updated"),
        auto_now=True,
        blank=True,
        null=True,
    )

    class Meta:
        abstract = True

    def __init__(self, *args, **kwargs):
        changelog_message = kwargs.pop("changelog_message", None)
        super().__init__(*args, **kwargs)
        self._changelog_message = changelog_message

    def serialize_object(self, exclude=None):
        """
        Return a JSON representation of the instance. Models can override this method to replace or extend the default
        serialization logic provided by the `serialize_object()` utility function.

        Args:
            exclude: An iterable of attribute names to omit from the serialized output
        """
        return serialize_object(self, exclude=exclude or [])

    def snapshot(self):
        """
        Save a snapshot of the object's current state in preparation for modification. The snapshot is saved as
        `_prechange_snapshot` on the instance.
        """
        exclude_fields = []
        if settings.CHANGELOG_SKIP_EMPTY_CHANGES:
            exclude_fields = [
                "last_updated",
            ]

        self._prechange_snapshot = self.serialize_object(exclude=exclude_fields)

    snapshot.alters_data = True

    def to_objectchange(self, action):
        """
        Return a new ObjectChange representing a change made to this object. This will typically be called automatically
        by ChangeLoggingMiddleware.
        """

        exclude = []
        if settings.CHANGELOG_SKIP_EMPTY_CHANGES:
            exclude = ["last_updated"]

        objectchange = ObjectChange(
            changed_object=self,
            object_repr=str(self)[:200],
            action=action,
            message=self._changelog_message or "",
        )
        if hasattr(self, "_prechange_snapshot"):
            objectchange.prechange_data = self._prechange_snapshot
        if action in (ObjectChangeActionChoices.ACTION_CREATE, ObjectChangeActionChoices.ACTION_UPDATE):
            self._postchange_snapshot = self.serialize_object(exclude=exclude)
            objectchange.postchange_data = self._postchange_snapshot

        return objectchange

    to_objectchange.alters_data = True


class CloningMixin(models.Model):
    """
    Provides the clone() method used to prepare a copy of existing objects.
    """

    class Meta:
        abstract = True

    def clone(self):
        """
        Returns a dictionary of attributes suitable for creating a copy of the current instance. This is used for pre-
        populating an object creation form in the UI. By default, this method will replicate any fields listed in the
        model's `clone_fields` list (if defined), but it can be overridden to apply custom logic.

        ```python
        class MyModel(ColdFrontModel):
            def clone(self):
                attrs = super().clone()
                attrs["extra-value"] = 123
                return attrs
        ```
        """
        attrs = {}

        for field_name in getattr(self, "clone_fields", []):
            field = self._meta.get_field(field_name)
            field_value = field.value_from_object(self)
            if field_value and isinstance(field, models.ManyToManyField):
                attrs[field_name] = [v.pk for v in field_value]
            elif field_value and isinstance(field, models.JSONField):
                attrs[field_name] = json.dumps(field_value)
            elif field_value not in (None, ""):
                attrs[field_name] = field_value

        # Handle GenericForeignKeys. If the CT and ID fields are being cloned, also
        # include the name of the GFK attribute itself, as this is what forms expect.
        for field in self._meta.private_fields:
            if isinstance(field, GenericForeignKey):
                if field.ct_field in attrs and field.fk_field in attrs:
                    attrs[field.name] = attrs[field.fk_field]

        # Include tags (if applicable)
        if is_taggable(self):
            attrs["tags"] = [tag.pk for tag in self.tags.all()]

        # Include any cloneable custom fields
        if hasattr(self, "custom_fields"):
            for field in self.custom_fields:
                if field.is_cloneable:
                    attrs[f"cf_{field.name}"] = self.custom_field_data.get(field.name)

        return attrs


class TagsMixin(models.Model):
    """
    Enables support for tag assignment. Assigned tags can be managed via the `tags` attribute,
    which is a `TaggableManager` instance.
    """

    tags = TaggableManager(
        through="core.TaggedItem",
        ordering=("weight", "name"),
    )

    class Meta:
        abstract = True


class CustomFieldsMixin(models.Model):
    """
    Enables support for custom fields.
    """

    custom_field_data = models.JSONField(encoder=CustomFieldJSONEncoder, blank=True, default=dict)

    class Meta:
        abstract = True

    @cached_property
    def cf(self):
        """
        Return a dictionary mapping each custom field for this instance to its deserialized value.

        ```python
        >>> tenant = Tenant.objects.first()
        >>> tenant.cf
        {'primary_site': <Site: DM-NYC>, 'cust_id': 'DMI01', 'is_active': True}
        ```
        """
        return {cf.name: cf.deserialize(self.custom_field_data.get(cf.name)) for cf in self.custom_fields}

    @cached_property
    def custom_fields(self):
        """
        Return the QuerySet of CustomFields assigned to this model.

        ```python
        >>> tenant = Tenant.objects.first()
        >>> tenant.custom_fields
        <RestrictedQuerySet [<CustomField: Primary site>, <CustomField: Customer ID>, <CustomField: Is active>]>
        ```
        """
        from coldfront.core.models import CustomField

        return CustomField.objects.get_for_model(self)

    def get_custom_fields(self, omit_hidden=False):
        """
        Return a dictionary of custom fields for a single object in the form `{field: value}`.

        ```python
        >>> tenant = Tenant.objects.first()
        >>> tenant.get_custom_fields()
        {<CustomField: Customer ID>: 'CYB01'}
        ```

        Args:
            omit_hidden: If True, custom fields with no UI visibility will be omitted.
        """
        from coldfront.core.models import CustomField

        data = {}

        for field in CustomField.objects.get_for_model(self):
            value = self.custom_field_data.get(field.name)

            # Skip hidden fields if 'omit_hidden' is True
            if omit_hidden and field.ui_visible == CustomFieldUIVisibleChoices.HIDDEN:
                continue
            if omit_hidden and field.ui_visible == CustomFieldUIVisibleChoices.IF_SET and not value:
                continue

            data[field] = field.deserialize(value)

        return data

    def get_custom_fields_by_group(self):
        """
        Return a dictionary of custom field/value mappings organized by group. Hidden fields are omitted.

        ```python
        >>> tenant = Tenant.objects.first()
        >>> tenant.get_custom_fields_by_group()
        {
            '': {<CustomField: Primary site>: <Site: DM-NYC>},
            'Billing': {<CustomField: Customer ID>: 'DMI01', <CustomField: Is active>: True}
        }
        ```
        """
        from coldfront.core.models import CustomField

        groups = defaultdict(dict)
        visible_custom_fields = CustomField.objects.get_for_model(self).exclude(
            ui_visible=CustomFieldUIVisibleChoices.HIDDEN
        )

        for cf in visible_custom_fields:
            value = self.custom_field_data.get(cf.name)
            if value in CUSTOMFIELD_EMPTY_VALUES and cf.ui_visible == CustomFieldUIVisibleChoices.IF_SET:
                continue
            value = cf.deserialize(value)
            groups[cf.group_name][cf] = value

        return dict(groups)

    def populate_custom_field_defaults(self):
        """
        Apply the default value for each custom field
        """
        for cf in self.custom_fields:
            self.custom_field_data[cf.name] = cf.default

    populate_custom_field_defaults.alters_data = True

    def clean(self):
        super().clean()
        from coldfront.core.models import CustomField

        custom_fields = {cf.name: cf for cf in CustomField.objects.get_for_model(self)}

        # Remove any stale custom field data
        self.custom_field_data = {k: v for k, v in self.custom_field_data.items() if k in custom_fields.keys()}

        # Validate all field values
        for field_name, value in self.custom_field_data.items():
            try:
                custom_fields[field_name].validate(value)
            except ValidationError as e:
                raise ValidationError(
                    _("Invalid value for custom field '{name}': {error}").format(name=field_name, error=e.message)
                )

            # Validate uniqueness if enforced
            if custom_fields[field_name].unique and value not in CUSTOMFIELD_EMPTY_VALUES:
                if (
                    self._meta.model.objects.exclude(pk=self.pk)
                    .filter(**{f"custom_field_data__{field_name}": value})
                    .exists()
                ):
                    raise ValidationError(_("Custom field '{name}' must have a unique value.").format(name=field_name))

        # Check for missing required values
        for cf in custom_fields.values():
            if cf.required and cf.name not in self.custom_field_data:
                raise ValidationError(_("Missing required custom field '{name}'.").format(name=cf.name))

    def save(self, *args, **kwargs):
        from coldfront.core.models import CustomField

        # Populate default values for custom fields not already present in the object data
        for cf in CustomField.objects.get_for_model(self):
            if cf.name not in self.custom_field_data and cf.default is not None:
                self.custom_field_data[cf.name] = cf.default

        super().save(*args, **kwargs)


class CustomLinksMixin(models.Model):
    """
    Enables support for custom links.
    """

    class Meta:
        abstract = True


class AllocatableResourceMixin(models.Model):
    """
    Enables support for allocatable resources. Models inheriting from this mixin
    represent resources that can be allocated to users. An option schema can be
    provided for storing custom allocation attributes.
    """

    name = models.CharField(
        verbose_name=_("name"),
        max_length=100,
    )

    schema = models.JSONField(
        blank=True,
        null=True,
        validators=[validate_schema],
        verbose_name=_("schema"),
    )

    locked = models.BooleanField(
        verbose_name=_("locked"),
        default=False,
        help_text=_("Prevent users from submitting allocations for this resource."),
    )

    class Meta:
        abstract = True

    def allocatable(self, user):
        """Checks if this resource is allocatable. Override to provide custom checks"""
        return not self.locked


register_model_feature("change_logging", lambda model: issubclass(model, ChangeLoggingMixin))
register_model_feature("cloning", lambda model: issubclass(model, CloningMixin))
register_model_feature("tags", lambda model: issubclass(model, TagsMixin))
register_model_feature("custom_fields", lambda model: issubclass(model, CustomFieldsMixin))
register_model_feature("allocatable_resource", lambda model: issubclass(model, AllocatableResourceMixin))
register_model_feature("commenting", lambda model: issubclass(model, CommentingMixin))
register_model_feature("custom_links", lambda model: issubclass(model, CustomLinksMixin))


def register_models(*models):
    """
    Register one or more models in ColdFront. This entails:

     - Determining whether the model is considered "public" (available for reference by other models)
     - Registering which features the model supports (e.g. bookmarks, custom fields, etc.)
     - Registering any feature-specific views for the model (e.g. ObjectCommentsView instances)

    register_model() should be called for each relevant model under the ready() of an app's AppConfig class.
    """
    for model in models:
        app_label, model_name = model._meta.label_lower.split(".")

        # Register applicable feature views for the model
        if issubclass(model, ChangeLoggingMixin):
            register_model_view(model, "changelog", kwargs={"model": model})(
                "coldfront.views.generic.ObjectChangeLogView"
            )
        if issubclass(model, CommentingMixin):
            register_model_view(model, "comments", kwargs={"model": model})("coldfront.core.views.ObjectCommentsView")

        # Auto-register custom permission actions declared in Meta.permissions
        if meta_permissions := getattr(model._meta, "permissions", None):
            actions = [ModelAction(codename, help_text=_(name)) for codename, name in meta_permissions]
            if actions:
                register_model_actions(model, actions)
