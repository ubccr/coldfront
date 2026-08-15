# SPDX-FileCopyrightText: (C) DigitalOcean, LLC
# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from dataclasses import dataclass

from django.apps import apps
from django.conf import settings
from django.db.models import Model, Q
from django.utils.translation import gettext_lazy as _

from coldfront.registry import registry

from .constants import CONSTRAINT_TOKEN_USER, RESERVED_ACTIONS

__all__ = (
    "ModelAction",
    "get_permission_for_model",
    "permission_is_exempt",
    "qs_filter_from_constraints",
    "register_model_actions",
    "resolve_permission",
    "resolve_permission_type",
)


@dataclass
class ModelAction:
    """
    Represents a custom permission action for a model.

    Attributes:
        name: The action identifier (e.g. 'sync', 'render_config')
        help_text: Optional description displayed in the ObjectPermission form
    """

    name: str
    help_text: str = ""

    def __post_init__(self):
        if not self.name:
            raise ValueError("Action name must not be empty.")
        if self.name in RESERVED_ACTIONS:
            raise ValueError(f"'{self.name}' is a reserved action and cannot be registered.")

    def __hash__(self):
        return hash(self.name)

    def __eq__(self, other):
        if isinstance(other, ModelAction):
            return self.name == other.name
        return self.name == other


def register_model_actions(model: type[Model], actions: list[ModelAction | str]):
    """
    Register custom permission actions for a model. These actions will appear as
    checkboxes in the ObjectPermission form when the model is selected.

    Args:
        model: The model class to register actions for
        actions: A list of ModelAction instances or action name strings
    """
    label = f"{model._meta.app_label}.{model._meta.model_name}"
    for action in actions:
        if isinstance(action, str):
            action = ModelAction(name=action)
        registry["model_actions"][label].add(action)


def get_permission_for_model(model, action):
    """
    Resolve the named permission for a given model (or instance) and action (e.g. view or add).

    :param model: A model or instance
    :param action: View, add, change, or delete (string)
    """
    # Resolve to the "concrete" model (for proxy models)
    model = model._meta.concrete_model

    return f"{model._meta.app_label}.{action}_{model._meta.model_name}"


def resolve_permission(name):
    """
    Given a permission name, return the app_label, action, and model_name components. For example, "ras.view_allocation"
    returns ("ras", "view", "allocation").

    :param name: Permission name in the format <app_label>.<action>_<model>
    """
    try:
        app_label, codename = name.split(".")
        action, model_name = codename.rsplit("_", 1)
    except ValueError:
        raise ValueError(
            _("Invalid permission name: {name}. Must be in the format <app_label>.<action>_<model>").format(name=name)
        )

    return app_label, action, model_name


def resolve_permission_type(name):
    """
    Given a permission name, return the relevant ObjectType and action. For example, "ras.view_allocation" returns
    (Allocation, "view").

    :param name: Permission name in the format <app_label>.<action>_<model>
    """
    from coldfront.core.models import ObjectType

    app_label, action, model_name = resolve_permission(name)
    try:
        object_type = ObjectType.objects.get_by_natural_key(app_label=app_label, model=model_name)
    except ObjectType.DoesNotExist:
        raise ValueError(_("Unknown app_label/model_name for {name}").format(name=name))

    return object_type, action


def permission_is_exempt(name):
    """
    Determine whether a specified permission is exempt from evaluation.

    :param name: Permission name in the format <app_label>.<action>_<model>
    """
    app_label, action, model_name = resolve_permission(name)

    if action == "view":
        if (
            # All models (excluding those in EXEMPT_EXCLUDE_MODELS) are exempt from view permission enforcement
            "*" in settings.EXEMPT_VIEW_PERMISSIONS and (app_label, model_name) not in settings.EXEMPT_EXCLUDE_MODELS
        ) or (
            # This specific model is exempt from view permission enforcement
            f"{app_label}.{model_name}" in settings.EXEMPT_VIEW_PERMISSIONS
        ):
            return True

    return False


def qs_filter_from_constraints(constraints, tokens=None):
    """
    Construct a Q filter object from an iterable of ObjectPermission constraints.

    Supports ``$queryset`` expressions for dynamic subquery constraints:
    constraints can include dict values with a ``$queryset`` key that specifies
    a model and filter to resolve as a Django QuerySet. This enables filtering
    through GenericForeignKey relationships and other scenarios requiring
    subqueries.

    Example YAML::

        assigned_object_id__in:
          $queryset:
            model: ras.allocation
            filter:
              project__owner: $user

    Args:
        tokens: A dictionary mapping string tokens to be replaced with a value.
    """
    if tokens is None:
        tokens = {}

    User = apps.get_model("users.User")
    for token, value in tokens.items():
        if token == CONSTRAINT_TOKEN_USER and isinstance(value, User):
            tokens[token] = value.id

    def _resolve_queryset(value, tokens):
        """Resolve a ``$queryset`` dict to a Django QuerySet of PKs."""
        qs_config = value["$queryset"]
        app_label, model_name = qs_config["model"].split(".")
        try:
            model = apps.get_model(app_label, model_name)
        except LookupError as e:
            raise ValueError(
                _("Unknown model '{model}' in $queryset constraint").format(model=qs_config["model"])
            ) from e
        if model is None:
            raise ValueError(_("Unknown model '{model}' in $queryset constraint").format(model=qs_config["model"]))
        resolved = {}
        for k, v in qs_config.get("filter", {}).items():
            resolved[k] = _replace_tokens(v, tokens)
        return model.objects.filter(**resolved).values_list("pk", flat=True)

    def _replace_tokens(value, tokens):
        if type(value) is list:
            return list(map(lambda v: _replace_tokens(v, tokens), value))
        if isinstance(value, dict) and "$queryset" in value:
            return _resolve_queryset(value, tokens)
        return tokens.get(value, value)

    params = Q()
    for constraint in constraints:
        if constraint:
            params |= Q(**{k: _replace_tokens(v, tokens) for k, v in constraint.items()})
        else:
            # Found null constraint; permit model-level access
            return Q()

    return params
