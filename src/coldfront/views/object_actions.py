# SPDX-FileCopyrightText: (C) DigitalOcean, LLC
# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django.db.models import ForeignKey
from django.urls.exceptions import NoReverseMatch
from django.utils.translation import gettext_lazy as _
from django_cotton import render_component

from coldfront.core.models import ObjectType
from coldfront.utils.querydict import prepare_cloned_fields

from .utils import get_action_url

__all__ = (
    "AddObject",
    "BulkDelete",
    "BulkEdit",
    "BulkExport",
    "BulkImport",
    "BulkRename",
    "CloneObject",
    "DeleteObject",
    "EditObject",
    "ObjectAction",
)


class ObjectAction:
    """
    Base class for single- and multi-object operations. A declarative Python
    representation of a c-cf.button: the class attributes map directly onto the
    button component's props/passthrough attrs, and render() builds the prop
    dict that c-cf.button receives.

    Params:
        name: The action name appended to the module for view resolution
        transition: The transition name if this action is associated with a workflow
        label: Label rendered on the button (c-cf.button label prop / slot)
        icon: The icon name rendered on the button (heroicon.* / tablericon.* / lucideicon.*)
        icon_class: Extra classes applied to the button icon (default "")
        icon_size: Size of the icon (default "")
        icon_end: End-position icon name (c-cf.button icon.end)
        icon_variant: Icon pack variant (c-cf.button icon.variant)
        variant: The daisyUI button colour variant
        as_: The c-cf.button element type — "a" (link), "button", "input", or "div"
        modal: True renders the button as an htmx modal trigger (hx-get + boilerplate)
        type: The passthrough type attr (e.g. "submit" for form submit buttons)
        behavior: The c-cf.button state — "active" or "disabled"
        size: The c-cf.button size (default "md")
        modifier: The c-cf.button modifier (e.g. "square")
        class_: Extra classes passed through to the button
        submit_name: The form field name for submit buttons (renders as name)
        icon_only: Render the button with just its icon, no label
        template_name: Name of the HTML template which renders the button
        multi: Set to True if this action is performed by selecting multiple objects
        permissions_required: The set of permissions a user must have to perform the action
        url_kwargs: The set of URL keyword arguments to pass when resolving the view's URL
    """

    name = ""
    transition = None
    label = ""
    icon = ""
    icon_class = ""
    icon_size = ""
    icon_end = ""
    icon_variant = ""
    variant = "primary"
    as_ = "button"
    modal = False
    type = ""
    behavior = ""
    size = "md"
    modifier = ""
    class_ = ""
    submit_name = ""
    icon_only = False
    template_name = "cf.button"
    multi = False
    permissions_required = set()
    url_kwargs = []

    @classmethod
    def get_url(cls, obj):
        kwargs = {kwarg: getattr(obj, kwarg) for kwarg in cls.url_kwargs}
        try:
            return get_action_url(obj, action=cls.name, kwargs=kwargs)
        except NoReverseMatch:
            return

    @classmethod
    def get_url_params(cls, context, obj=None):
        """Return the query params appended to a submit button's formaction URL."""
        request = context["request"]
        params = request.GET.copy()
        if "return_url" in context:
            params["return_url"] = context["return_url"]
        return params

    @classmethod
    def get_context(cls, context, obj):
        """Return template-only extras forwarded to the rendered template."""
        return {}

    @classmethod
    def build_attrs(cls, context, obj, url):
        """Build the c-cf.button prop/attr dict from the declarative fields."""
        extras = cls.get_context(context, obj)
        url_params = cls.get_url_params(context, obj)
        return_url = context.get("return_url", "")

        attrs = {
            "label": cls.label,
            "icon": cls.icon,
            "icon.class": cls.icon_class,
            "icon.size": cls.icon_size,
            "icon.end": cls.icon_end,
            "icon.variant": cls.icon_variant,
            "variant": cls.variant,
            "behavior": cls.behavior,
            "as": cls.as_,
            "size": cls.size,
            "modifier": cls.modifier,
            "class": cls.class_,
        }

        if url:
            if cls.as_ == "a":
                attrs["href"] = url + (f"?return_url={return_url}" if return_url else "")
            elif cls.modal:
                attrs["hx-get"] = url + "?_modal=True"
                attrs["hx-target"] = "#htmxModal-content"
                attrs["hx-swap"] = "innerHTML"
                attrs["hx-on::before-request"] = "document.getElementById('htmxModal-content').innerHTML = '';"
                attrs["onclick"] = "htmxModal.showModal()"
            elif cls.as_ in ("button", "input") and cls.type == "submit":
                attrs["formaction"] = url + (f"?{url_params.urlencode()}" if url_params else "")
                attrs["name"] = cls.submit_name

        if cls.icon_only:
            attrs["modifier"] = "square"
            attrs["label"] = ""

        attrs.update(**extras)
        return attrs

    @classmethod
    def render(cls, context, obj, **kwargs):
        attrs = cls.build_attrs(context, obj, cls.get_url(obj))
        attrs.update(**kwargs)
        return render_component(context["request"], cls.template_name, attrs)


class AddObject(ObjectAction):
    """
    Create a new object.
    """

    name = "add"
    label = _("Add")
    icon = "tablericon.plus"
    variant = "primary"
    as_ = "a"
    permissions_required = {"add"}


class CloneObject(ObjectAction):
    """
    Populate the new object form with select details from an existing object.
    """

    name = "add"
    label = _("Clone")
    icon = "heroicon.document-duplicate"
    variant = "info"
    as_ = "a"
    permissions_required = {"add"}

    @classmethod
    def get_url(cls, obj):
        url = super().get_url(obj)
        param_string = prepare_cloned_fields(obj).urlencode()
        return f"{url}?{param_string}" if param_string else None


class EditObject(ObjectAction):
    """
    Edit a single object.
    """

    name = "edit"
    label = _("Edit")
    icon = "lucideicon.pen-square"
    variant = "warning"
    as_ = "a"
    permissions_required = {"change"}
    url_kwargs = ["pk"]


class DeleteObject(ObjectAction):
    """
    Delete a single object.
    """

    name = "delete"
    label = _("Delete")
    icon = "heroicon.trash"
    variant = "error"
    modal = True
    permissions_required = {"delete"}
    url_kwargs = ["pk"]


class BulkImport(ObjectAction):
    """
    Import multiple objects at once.
    """

    name = "bulk_import"
    label = _("Import")
    icon = "heroicon.arrow-up-tray"
    variant = "secondary"
    as_ = "a"
    permissions_required = {"add"}


class BulkExport(ObjectAction):
    """
    Export multiple objects at once.
    """

    name = "export"
    label = _("Export")
    icon = "heroicon.arrow-down-tray"
    variant = "info"
    permissions_required = {"view"}
    template_name = "cf.button.export"

    @classmethod
    def get_context(cls, context, model):
        object_type = ObjectType.objects.get_for_model(model)

        # Determine if the "all data" export returns CSV or YAML
        data_format = "YAML" if hasattr(object_type.model_class(), "to_yaml") else "CSV"

        return {
            "object_type": object_type,
            "url_params": context["request"].GET.urlencode() if context["request"].GET else "",
            "data_format": data_format,
        }


class BulkEdit(ObjectAction):
    """
    Change the value of one or more fields on a set of objects.
    """

    name = "bulk_edit"
    label = _("Edit Selected")
    icon = "lucideicon.pen-square"
    variant = "warning"
    type = "submit"
    submit_name = "_edit"
    multi = True
    permissions_required = {"change"}

    @classmethod
    def get_url_params(cls, context, obj):
        url_params = super().get_url_params(context, obj)

        # If this is a child object, pass the parent's PK as a URL parameter
        if parent := context.get("object"):
            for field in obj._meta.get_fields():
                if isinstance(field, ForeignKey) and field.remote_field.model == parent.__class__:
                    url_params[field.name] = parent.pk
                    break

        return url_params


class BulkRename(ObjectAction):
    """
    Rename multiple objects at once.
    """

    name = "bulk_rename"
    label = _("Rename Selected")
    icon = "lucideicon.pen-square"
    variant = "warning"
    type = "submit"
    submit_name = "_rename"
    multi = True
    permissions_required = {"change"}


class BulkDelete(ObjectAction):
    """
    Delete each of a set of objects.
    """

    name = "bulk_delete"
    label = _("Delete Selected")
    icon = "heroicon.trash"
    variant = "error"
    type = "submit"
    submit_name = "_delete"
    multi = True
    permissions_required = {"delete"}
