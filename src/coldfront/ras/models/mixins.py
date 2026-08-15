# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django.conf import settings
from django.core.exceptions import FieldDoesNotExist, ImproperlyConfigured
from django.db import models


class AllocationExtensionMixin(models.Model):
    """
    Abstract base mixin for allocation extension models.

    An allocation extension carries resource-specific data attached to an
    allocation.  Each concrete subclass (e.g., StorageQuota, SlurmAssociation)
    adds its own fields and is registered via ``register_allocation_extension()``.

    The ``allocation`` FK is unique — each allocation has at most one instance
    of each extension type.

    To expose fields in allocation request and change request forms, override
    ``requestable_fields()`` on the concrete subclass.
    """

    allocation = models.ForeignKey(
        to="ras.Allocation",
        on_delete=models.PROTECT,
        unique=True,
        related_name="%(app_label)s_%(class)s_extensions",
    )

    # Private default — subclasses set this or override requestable_fields().
    _requestable_fields = None

    class Meta:
        abstract = True

    @classmethod
    def requestable_fields(cls):
        """
        Return the list of field names exposed in allocation/change request forms.

        Override on concrete subclasses.  ``None`` or empty = no fields exposed.
        The default reads from ``cls._requestable_fields``.

        Centers can override this per extension model via the
        ``ALLOCATION_EXTENSION_REQUESTABLE_FIELDS`` setting without writing
        Python code.  The setting key is the fully-qualified class path,
        e.g. ``"coldfront.slurm.models.SlurmAssociation"``.
        """
        overrides = settings.ALLOCATION_EXTENSION_REQUESTABLE_FIELDS
        key = f"{cls.__module__}.{cls.__qualname__}"
        if key in overrides:
            fields = overrides[key]
            # Validate that all named fields exist on the model
            for field_name in fields:
                try:
                    cls._meta.get_field(field_name)
                except FieldDoesNotExist:
                    msg = (
                        f"ALLOCATION_EXTENSION_REQUESTABLE_FIELDS for '{key}' "
                        f"includes '{field_name}', which is not a field on {cls.__qualname__}."
                    )
                    raise ImproperlyConfigured(msg)
            return list(fields)
        fields = cls._requestable_fields
        if fields is None:
            return []
        return list(fields)

    @classmethod
    def requestable_fields_overrides(cls):
        """
        Return a dict mapping field names to custom Django form fields.

        Override on concrete subclasses to replace auto-generated form fields
        with custom widgets, validation, or field types.  The default returns
        an empty dict (no overrides).
        """
        return {}

    @classmethod
    def create_for_allocation(cls, allocation, values=None):
        """
        Create an extension instance for the given allocation.

        Override this to provide custom creation logic (e.g., setting defaults
        or auto-computing field values).  By default, creates an instance with
        the given values dict (or no values, relying on field defaults).
        """
        kwargs = {}
        if values is not None:
            for field_name in cls.requestable_fields():
                if field_name in values:
                    kwargs[field_name] = values[field_name]
        instance = cls(allocation=allocation, **kwargs)
        instance.full_clean()
        instance.save()
        return instance

    def apply_json_change(self, values):
        """
        Apply a dict of proposed values from a change request to this extension.

        Only fields listed in ``requestable_fields()`` are applied.
        Override this for custom validation or side-effects.

        Values from ``extension_changes`` JSON are stored in a format
        compatible with Django's field.to_python() (e.g., duration strings
        like "3:00:00" for DurationField).  This method uses the model
        field's own to_python() method for type conversion.
        Validation is handled by full_clean() afterwards.
        """
        changed = False
        for field_name in self.requestable_fields():
            if field_name in values:
                new_value = values[field_name]
                if new_value is not None:
                    field = self._meta.get_field(field_name)
                    setattr(self, field_name, field.to_python(new_value))
                    changed = True
        if changed:
            self.full_clean()
            self.save()
