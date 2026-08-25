# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django.conf import settings
from django.core.exceptions import FieldDoesNotExist, ImproperlyConfigured, ValidationError
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

    # Private default — subclasses set this or override changeable_fields().
    # Changeable fields are exposed ONLY on the allocation change request form.
    # Values may be plain field names or related-object markers of the form
    # ``$related:<fk>.<field>``, which flag a ForeignKey on this extension and a
    # requestable field on the FK's target model.
    _changeable_fields = None

    # Prefix marking a related-object field token in ``_changeable_fields``.
    RELATED_FIELD_PREFIX = "$related:"

    class Meta:
        abstract = True

    @classmethod
    def is_related_field_token(cls, token):
        """Return True if ``token`` is a related-object marker."""
        return isinstance(token, str) and token.startswith(cls.RELATED_FIELD_PREFIX)

    @classmethod
    def parse_related_field_token(cls, token):
        """
        Parse a ``$related:<fk>.<field>`` token into ``(fk_name, target_field)``.

        Raises ImproperlyConfigured if the token is not well-formed.
        """
        body = token[len(cls.RELATED_FIELD_PREFIX) :]
        parts = body.split(".")
        if len(parts) != 2:
            raise ImproperlyConfigured(
                f"Changeable field '{token}' must use the form '$related:<fk>.<field>' on {cls.__qualname__}."
            )
        return parts[0], parts[1]

    @classmethod
    def _validate_field_tokens(cls, tokens, setting_name):
        """Validate that scalar tokens are fields and related markers resolve."""
        for token in tokens:
            if cls.is_related_field_token(token):
                fk_name, target_field = cls.parse_related_field_token(token)
                try:
                    fk = cls._meta.get_field(fk_name)
                except FieldDoesNotExist:
                    raise ImproperlyConfigured(
                        f"{setting_name} for '{cls.__qualname__}' includes '{token}', "
                        f"whose FK '{fk_name}' is not a field on {cls.__qualname__}."
                    )
                if not isinstance(fk, models.ForeignKey):
                    raise ImproperlyConfigured(
                        f"{setting_name} for '{cls.__qualname__}' includes '{token}', "
                        f"but '{fk_name}' is not a ForeignKey on {cls.__qualname__}."
                    )
                target_model = fk.remote_field.model
                try:
                    target_model._meta.get_field(target_field)
                except FieldDoesNotExist:
                    raise ImproperlyConfigured(
                        f"{setting_name} for '{cls.__qualname__}' includes '{token}', "
                        f"but '{target_field}' is not a field on {target_model.__qualname__}."
                    )
            else:
                try:
                    cls._meta.get_field(token)
                except FieldDoesNotExist:
                    raise ImproperlyConfigured(
                        f"{setting_name} for '{cls.__qualname__}' includes '{token}', "
                        f"which is not a field on {cls.__qualname__}."
                    )

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
            fields = list(overrides[key])
            for field_name in fields:
                if cls.is_related_field_token(field_name):
                    raise ImproperlyConfigured(
                        f"Related-object markers are only supported in changeable "
                        f"fields, not ALLOCATION_EXTENSION_REQUESTABLE_FIELDS "
                        f"for '{key}'."
                    )
            cls._validate_field_tokens(fields, "ALLOCATION_EXTENSION_REQUESTABLE_FIELDS")
            return fields
        fields = cls._requestable_fields
        if fields is None:
            return []
        fields = list(fields)
        for field_name in fields:
            if cls.is_related_field_token(field_name):
                raise ImproperlyConfigured(
                    f"Related-object markers are only supported in changeable "
                    f"fields, not in '_requestable_fields' on {cls.__qualname__}."
                )
        return fields

    @classmethod
    def changeable_fields(cls):
        """
        Return the list of field tokens exposed ONLY on the allocation change
        request form.

        Override on concrete subclasses.  ``None`` or empty = no fields exposed.
        The default reads from ``cls._changeable_fields``.  Tokens may be plain
        field names or related-object markers (``$related:<fk>.<field>``).

        Centers can override this per extension model via the
        ``ALLOCATION_EXTENSION_CHANGEABLE_FIELDS`` setting without writing
        Python code.  The setting key is the fully-qualified class path.
        """
        overrides = settings.ALLOCATION_EXTENSION_CHANGEABLE_FIELDS
        key = f"{cls.__module__}.{cls.__qualname__}"
        if key in overrides:
            fields = list(overrides[key])
            cls._validate_field_tokens(fields, "ALLOCATION_EXTENSION_CHANGEABLE_FIELDS")
            return fields
        fields = cls._changeable_fields
        if fields is None:
            return []
        return list(fields)

    @classmethod
    def fields_for_change(cls):
        """Return requestable + changeable field tokens (used on change requests)."""
        return cls.requestable_fields() + cls.changeable_fields()

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
        Apply a dict of proposed values from a change request to this extension
        and its related-object targets.

        Only fields listed in ``fields_for_change()`` are applied.  Plain field
        names are applied to this extension; related-object markers
        (``$related:<fk>.<field>``) are applied to the FK target instance.
        Override this for custom validation or side-effects.

        Values from ``extension_changes`` JSON are stored in a format
        compatible with Django's field.to_python() (e.g., duration strings
        like "3:00:00" for DurationField).  This method uses the model
        field's own to_python() method for type conversion.
        Validation is handled by full_clean() afterwards.
        """
        self_changed = False
        changed_targets = set()
        for token in self.fields_for_change():
            if self.is_related_field_token(token):
                fk_name, target_field = self.parse_related_field_token(token)
                if target_field in values and values[target_field] is not None:
                    target = getattr(self, fk_name)
                    if target is None:
                        # The related object is not set yet — abort loudly so the
                        # change can't be silently dropped.  The flow converts
                        # this ValidationError into an AbortRequest.
                        fk_label = str(self._meta.get_field(fk_name).verbose_name).capitalize()
                        target_model = self._meta.get_field(fk_name).remote_field.model
                        field_label = str(target_model._meta.get_field(target_field).verbose_name).capitalize()
                        raise ValidationError(
                            f"{fk_label} is not set on this {str(self._meta.verbose_name)} — "
                            f"{field_label} cannot be changed until one is set."
                        )
                    field = target._meta.get_field(target_field)
                    setattr(target, target_field, field.to_python(values[target_field]))
                    changed_targets.add(target)
            else:
                if token in values and values[token] is not None:
                    field = self._meta.get_field(token)
                    setattr(self, token, field.to_python(values[token]))
                    self_changed = True
        if self_changed:
            self.full_clean()
            self.save()
        for target in changed_targets:
            target.full_clean()
            target.save()
