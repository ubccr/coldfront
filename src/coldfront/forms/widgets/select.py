# SPDX-FileCopyrightText: (C) DigitalOcean, LLC
# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django import forms


class HTMXSelectWidget(forms.Select):
    """
    Selection widget that will re-generate the HTML form upon the selection of a new option.
    """

    def __init__(self, method="get", hx_url=".", hx_target_id="form_fields", attrs=None, **kwargs):
        method = method.lower()
        if method not in ("delete", "get", "patch", "post", "put"):
            raise ValueError(f"Unsupported HTTP method: {method}")
        _attrs = {
            f"hx-{method}": hx_url,
            "hx-include": f"#{hx_target_id}",
            "hx-params": "not csrfmiddlewaretoken",
            "hx-target": f"#{hx_target_id}",
        }
        if attrs:
            _attrs.update(attrs)

        super().__init__(attrs=_attrs, **kwargs)


class BulkEditNullBooleanSelect(forms.NullBooleanSelect):
    """
    A Select widget for NullBooleanFields
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Override the built-in choice labels
        self.choices = (
            ("1", "---------"),
            ("2", "Yes"),
            ("3", "No"),
        )
