# SPDX-FileCopyrightText: (C) DigitalOcean, LLC
# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from typing import cast

from django import forms
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.db import models
from django.db.models.fields import SlugField
from django.utils.module_loading import import_string
from django.utils.safestring import mark_safe
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from coldfront.core.choices import ColorChoices
from coldfront.utils.forms import add_blank_choice
from coldfront.utils.validators import ColorValidator

try:
    AUTO_SLUG_FUNC = import_string(settings.AUTO_SLUG_FUNC)
except ImportError:
    raise ImproperlyConfigured("AUTO_SLUG_FUNC was set but cannot be imported. Please check your config settings.")


class ColorField(models.CharField):
    default_validators = [ColorValidator]
    description = "A hexadecimal RGB color code"

    def __init__(self, *args, **kwargs):
        kwargs["max_length"] = 6
        super().__init__(*args, **kwargs)

    def formfield(self, **kwargs):
        kwargs["widget"] = forms.Select(
            choices=add_blank_choice(ColorChoices),
            attrs={"class": "color-select"},
        )
        kwargs["help_text"] = mark_safe(_("RGB color in hexadecimal. Example: ") + "<code>00ff00</code>")
        return super().formfield(**kwargs)


class AutoSlugField(SlugField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("max_length", 50)
        kwargs.setdefault("editable", True)
        kwargs.setdefault("blank", True)
        kwargs.setdefault("unique", True)
        kwargs.setdefault("db_index", True)

        self.allow_unicode = kwargs.pop("allow_unicode", False)
        self.max_retries = 5

        super(SlugField, self).__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        if self.max_length == 50:
            kwargs.pop("max_length", None)

        return name, path, args, kwargs

    def _generate_unique_slug(self, instance):
        """Generate unique slug checking DB for collisions."""

        for _ in range(self.max_retries):  # noqa: F402
            value = AUTO_SLUG_FUNC(instance)
            value = slugify(value)

            if not instance.__class__.objects.filter(**{cast(str, self.name): value}).exists():
                return value

        raise ValidationError(f"Could not generate unique {self.name} after {self.max_retries} attempts")

    def pre_save(self, instance, add):
        value = super().pre_save(instance, add)

        if value is None or value == "":
            value = self._generate_unique_slug(instance)
            setattr(instance, self.name, value)

        return value
