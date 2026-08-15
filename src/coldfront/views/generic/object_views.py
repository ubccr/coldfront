# SPDX-FileCopyrightText: (C) DigitalOcean, LLC
# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

import logging
from collections import defaultdict

from django.contrib import messages
from django.core.exceptions import ImproperlyConfigured, PermissionDenied
from django.db import router, transaction
from django.db.models import ProtectedError, RestrictedError
from django.db.models.deletion import Collector
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.html import escape, format_html
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from django_cotton import render_component

from coldfront.exceptions import AbortRequest, PermissionsViolation
from coldfront.forms import ColdFrontModelForm, DeleteForm
from coldfront.tables import get_table_configs
from coldfront.users.permissions import get_permission_for_model
from coldfront.utils.forms import restrict_form_fields
from coldfront.utils.querydict import normalize_querydict, prepare_cloned_fields
from coldfront.utils.request import safe_for_redirect
from coldfront.views import get_action_url, handle_protectederror
from coldfront.views.htmx import htmx_partial
from coldfront.views.mixins import GetReturnURLMixin
from coldfront.views.object_actions import CloneObject, DeleteObject, EditObject

from .base import BaseObjectView
from .mixins import ActionsMixin, TableMixin

__all__ = (
    "ObjectDeleteView",
    "ObjectEditView",
    "ObjectView",
    "ObjectChildrenView",
)


class ObjectView(ActionsMixin, BaseObjectView):
    """
    Retrieve a single object for display.

    Note: If `template_name` is not specified, it will be determined automatically based on the queryset model.

    Attributes:
        tab: A ViewTab instance for the view
        actions: An iterable of ObjectAction subclasses (see ActionsMixin)
    """

    tab = None
    actions = (CloneObject, EditObject, DeleteObject)

    def get_required_permission(self):
        return get_permission_for_model(self.queryset.model, "view")

    def get_template_name(self):
        """
        Return self.template_name if defined. Otherwise, dynamically resolve the template name using the queryset
        model's `app_label` and `model_name`.
        """
        if self.template_name is not None:
            return self.template_name
        model_opts = self.queryset.model._meta
        return f"{model_opts.app_label}/{model_opts.model_name}.html"

    #
    # Request handlers
    #

    def get(self, request, **kwargs):
        """
        GET request handler. `*args` and `**kwargs` are passed to identify the object being queried.

        Args:
            request: The current request
        """
        instance = self.get_object(**kwargs)
        actions = self.get_permitted_actions(request.user, model=instance)

        return render(
            request,
            self.get_template_name(),
            {
                "object": instance,
                "actions": actions,
                "tab": self.tab,
                **self.get_extra_context(request, instance),
            },
        )


class ObjectEditView(GetReturnURLMixin, BaseObjectView):
    """
    Create or edit a single object.

    Attributes:
        form: The form used to create or edit the object
    """

    template_name = "generic/object_edit.html"
    form = None
    form_component_name = "form"

    def dispatch(self, request, *args, **kwargs):
        # Determine required permission based on whether we are editing an existing object
        self._permission_action = "change" if kwargs else "add"

        return super().dispatch(request, *args, **kwargs)

    def get_required_permission(self):
        # self._permission_action is set by dispatch() to either "add" or "change" depending on whether
        # we are modifying an existing object or creating a new one.
        return get_permission_for_model(self.queryset.model, self._permission_action)

    def get_object(self, **kwargs):
        """
        Return an object for editing. If no keyword arguments have been specified, this will be a new instance.
        """
        if not kwargs:
            # We're creating a new object
            return self.queryset.model()
        return super().get_object(**kwargs)

    def alter_object(self, obj, request, url_args, url_kwargs):
        """
        Provides a hook for views to modify an object before it is processed. For example, a parent object can be
        defined given some parameter from the request URL.

        Args:
            obj: The object being edited
            request: The current request
            url_args: URL path args
            url_kwargs: URL path kwargs
        """
        return obj

    def get_extra_addanother_params(self, request):
        """
        Return a dictionary of extra parameters to use on the Add Another button.
        """
        return {}

    def alter_form(self, form, request, obj):
        """
        Provides a hook for views to modify the form after it is created but
        before it is rendered or validated. For example, fields can be disabled
        based on the object's state.

        Args:
            form: The form being processed
            request: The current request
            obj: The object being edited
        """
        pass

    #
    # Request handlers
    #

    def get(self, request, *args, **kwargs):
        """
        GET request handler.

        Args:
            request: The current request
        """
        obj = self.get_object(**kwargs)
        obj = self.alter_object(obj, request, args, kwargs)
        model = self.queryset.model

        initial_data = normalize_querydict(request.GET)
        form_prefix = "quickadd" if request.GET.get("_quickadd") else None
        if issubclass(self.form, ColdFrontModelForm):
            form = self.form(instance=obj, initial=initial_data, prefix=form_prefix, user=request.user)
        else:
            form = self.form(instance=obj, initial=initial_data, prefix=form_prefix)

        restrict_form_fields(form, request.user)
        self.alter_form(form, request, obj)

        context = {
            "model": model,
            "object": obj,
            "form": form,
        }

        # If the form is being displayed within a "quick add" widget,
        # use the appropriate template
        if request.GET.get("_quickadd"):
            return render(request, "generic/quick_add.html", context)

        # If this is an HTMX request, return only the rendered form HTML
        if htmx_partial(request):
            return HttpResponse(render_component(request, self.form_component_name, context))

        return render(
            request,
            self.template_name,
            {
                **context,
                "return_url": self.get_return_url(request, obj),
                "prerequisite_model": self.get_prerequisite_model(),
                **self.get_extra_context(request, obj),
            },
        )

    def post(self, request, *args, **kwargs):
        """
        POST request handler.

        Args:
            request: The current request
        """
        logger = logging.getLogger("coldfront.views.ObjectEditView")
        obj = self.get_object(**kwargs)
        model = self.queryset.model

        # Take a snapshot for change logging (if editing an existing object)
        if obj.pk and hasattr(obj, "snapshot"):
            obj.snapshot()

        obj = self.alter_object(obj, request, args, kwargs)

        form_prefix = "quickadd" if request.GET.get("_quickadd") else None
        if issubclass(self.form, ColdFrontModelForm):
            form = self.form(
                data=request.POST, files=request.FILES, instance=obj, prefix=form_prefix, user=request.user
            )
        else:
            form = self.form(data=request.POST, files=request.FILES, instance=obj, prefix=form_prefix)

        restrict_form_fields(form, request.user)
        self.alter_form(form, request, obj)

        if form.is_valid():
            logger.debug("Form validation was successful")

            # Record changelog message (if any)
            obj._changelog_message = form.cleaned_data.pop("changelog_message", "")

            try:
                with transaction.atomic(using=router.db_for_write(model)):
                    object_created = form.instance.pk is None
                    obj = form.save()

                    # Check that the new object conforms with any assigned object-level permissions
                    if not self.queryset.filter(pk=obj.pk).exists():
                        raise PermissionsViolation()

                msg = "{} {}".format(
                    "Created" if object_created else "Modified", self.queryset.model._meta.verbose_name
                )
                logger.info(f"{msg} {obj} (PK: {obj.pk})")
                if hasattr(obj, "get_absolute_url"):
                    msg = format_html('{} <a href="{}">{}</a>', msg, obj.get_absolute_url(), escape(obj))
                else:
                    msg = f"{msg} {obj}"
                messages.success(request, msg)

                # Object was created via "quick add" modal
                if "_quickadd" in request.POST:
                    return render(
                        request,
                        "generic/quick_add_created.html",
                        {
                            "object": obj,
                        },
                    )

                # If adding another object, redirect back to the edit form
                if "_addanother" in request.POST:
                    redirect_url = request.path

                    # If cloning is supported, pre-populate a new instance of the form
                    params = prepare_cloned_fields(obj)
                    params.update(self.get_extra_addanother_params(request))
                    if params:
                        if "return_url" in request.GET:
                            params["return_url"] = request.GET.get("return_url")
                        redirect_url += f"?{params.urlencode()}"
                        if not safe_for_redirect(redirect_url):
                            redirect_url = reverse("home")

                    return redirect(redirect_url)

                return_url = self.get_return_url(request, obj)

                # If the object has been created or edited via HTMX, return an HTMX redirect to the object view
                if request.htmx:
                    return HttpResponse(
                        headers={
                            "HX-Location": return_url,
                        }
                    )

                return redirect(return_url)

            except (AbortRequest, PermissionsViolation) as e:
                logger.debug(e.message)
                form.add_error(None, e.message)

        else:
            logger.debug("Form validation failed")

        context = {
            "model": model,
            "object": obj,
            "form": form,
            "return_url": self.get_return_url(request, obj),
            **self.get_extra_context(request, obj),
        }

        # Form was submitted via a "quick add" widget
        if "_quickadd" in request.POST:
            return render(request, "generic/quick_add.html", context)

        return render(request, self.template_name, context)


class ObjectDeleteView(GetReturnURLMixin, BaseObjectView):
    """
    Delete a single object.
    """

    template_name = "generic/object_delete.html"

    def get_required_permission(self):
        return get_permission_for_model(self.queryset.model, "delete")

    def _get_dependent_objects(self, obj):
        """
        Returns a dictionary mapping of dependent objects (organized by model) which will be deleted as a result of
        deleting the requested object.

        Args:
            obj: The object to return dependent objects for
        """
        using = router.db_for_write(obj._meta.model)
        collector = Collector(using=using)
        collector.collect([obj])

        # Compile a mapping of models to instances
        dependent_objects = defaultdict(list)
        for model, instances in collector.instances_with_model():
            # Ignore relations to auto-created models (e.g. many-to-many mappings)
            if model._meta.auto_created:
                continue
            # Omit the root object
            if instances == obj:
                continue
            dependent_objects[model].append(instances)

        return dict(dependent_objects)

    def _handle_protected_objects(self, obj, protected_objects, request, exc):
        """
        Handle a ProtectedError or RestrictedError exception raised while attempt to resolve dependent objects.
        """
        handle_protectederror(protected_objects, request, exc)

        if request.htmx:
            return HttpResponse(
                headers={
                    "HX-Redirect": obj.get_absolute_url(),
                }
            )
        else:
            return redirect(obj.get_absolute_url())

    #
    # Request handlers
    #

    def get(self, request, *args, **kwargs):
        """
        GET request handler.

        Args:
            request: The current request
        """
        obj = self.get_object(**kwargs)
        form = DeleteForm(instance=obj, initial=request.GET)

        try:
            dependent_objects = self._get_dependent_objects(obj)
        except ProtectedError as e:
            return self._handle_protected_objects(obj, e.protected_objects, request, e)
        except RestrictedError as e:
            return self._handle_protected_objects(obj, e.restricted_objects, request, e)

        # If this is an HTMX request, return only the rendered deletion form as modal content
        if htmx_partial(request):
            form_url = get_action_url(self.queryset.model, action="delete", kwargs={"pk": obj.pk})
            return HttpResponse(
                render_component(
                    request,
                    "form.delete",
                    object=obj,
                    object_type=self.queryset.model._meta.verbose_name,
                    form=form,
                    form_url=form_url,
                    dependent_objects=dependent_objects,
                    **self.get_extra_context(request, obj),
                )
            )

        return render(
            request,
            self.template_name,
            {
                "object": obj,
                "form": form,
                "return_url": self.get_return_url(request, obj),
                "dependent_objects": dependent_objects,
                **self.get_extra_context(request, obj),
            },
        )

    def post(self, request, *args, **kwargs):
        """
        POST request handler.

        Args:
            request: The current request
        """
        logger = logging.getLogger("coldfront.views.ObjectDeleteView")
        obj = self.get_object(**kwargs)
        form = DeleteForm(request.POST, instance=obj)

        if form.is_valid():
            logger.debug("Form validation was successful")

            # Take a snapshot of change-logged models
            if hasattr(obj, "snapshot"):
                obj.snapshot()

            # Record changelog message (if any)
            obj._changelog_message = form.cleaned_data.pop("changelog_message", "")

            # Delete the object
            try:
                obj.delete()
            except (ProtectedError, RestrictedError) as e:
                logger.info(f"Caught {type(e)} while attempting to delete objects")
                handle_protectederror([obj], request, e)
                return redirect(obj.get_absolute_url())
            except AbortRequest as e:
                logger.debug(e.message)
                messages.error(request, mark_safe(e.message))
                return redirect(obj.get_absolute_url())

            msg = "Deleted {} {}".format(self.queryset.model._meta.verbose_name, obj)
            logger.info(msg)
            messages.success(request, msg)

            return_url = form.cleaned_data.get("return_url")
            if return_url and return_url.startswith("/"):
                return redirect(return_url)
            return redirect(self.get_return_url(request, obj))

        else:
            logger.debug("Form validation failed")

        return render(
            request,
            self.template_name,
            {
                "object": obj,
                "form": form,
                "return_url": self.get_return_url(request, obj),
                **self.get_extra_context(request, obj),
            },
        )


class ObjectChildrenView(ObjectView, ActionsMixin, TableMixin):
    """
    Display a table of child objects associated with the parent object. For example, ColdFront uses this to display
    the set of allocations for a project.

    Attributes:
        child_model: The model class which represents the child objects
        table: The django-tables2 Table class used to render the child objects list
        filterset: A django-filter FilterSet that is applied to the queryset
        filterset_form: The form class used to render filter options
        actions: An iterable of ObjectAction subclasses (see ActionsMixin)
    """

    child_model = None
    table = None
    filterset = None
    filterset_form = None
    actions = (CloneObject, EditObject, DeleteObject)
    template_name = "generic/object_children.html"

    def get_children(self, request, parent):
        """
        Return a QuerySet of child objects.

        Args:
            request: The current request
            parent: The parent object
        """
        raise NotImplementedError(
            _("{class_name} must implement get_children()").format(class_name=self.__class__.__name__)
        )

    def prep_table_data(self, request, queryset, parent):
        """
        Provides a hook for subclassed views to modify data before initializing the table.

        Args:
            request: The current request
            queryset: The filtered queryset of child objects
            parent: The parent object
        """
        return queryset

    #
    # Request handlers
    #

    def get(self, request, *args, **kwargs):
        """
        GET handler for rendering child objects.
        """
        instance = self.get_object(**kwargs)
        child_objects = self.get_children(request, instance)

        if self.filterset:
            child_objects = self.filterset(request.GET, child_objects, request=request).qs

        # Determine the available actions
        actions = self.get_permitted_actions(request.user, model=self.child_model)
        has_table_actions = any(action.multi for action in actions)

        table_data = self.prep_table_data(request, child_objects, instance)
        table = self.get_table(table_data, request, has_table_actions)

        # If this is an HTMX request, return only the rendered table HTML
        if htmx_partial(request):
            return HttpResponse(
                render_component(
                    request,
                    "table.htmx",
                    table=table,
                    model=self.child_model,
                )
            )

        return render(
            request,
            self.get_template_name(),
            {
                "object": instance,
                "model": self.child_model,
                "child_model": self.child_model,
                "base_template": f"{instance._meta.app_label}/{instance._meta.model_name}.html",
                "table": table,
                "table_config": f"{table.name}_config",
                "table_configs": get_table_configs(table, request.user),
                "filter_form": self.filterset_form(request.GET) if self.filterset_form else None,
                "actions": actions,
                "tab": self.tab,
                "return_url": request.get_full_path(),
                **self.get_extra_context(request, instance),
            },
        )


class ObjectFlowView(GetReturnURLMixin, BaseObjectView):
    """
    Edit an object that is part of a workflow. A workflow is a FSM that defines
    a set of states and transitions between them. An ObjectFlowView is a view
    for a specific transition in a workflow. It presents the form for the transition
    and in the POST will execute the transition.

    Attributes:
        form: The form used to edit the object
        flow: The workflow
        action: The ObjectAction that is assoicated with the transition in the
                workflow. The ObjectAction defines the required permissions and the
                transition that gets called
    """

    template_name = "generic/object_flow.html"
    form = None
    form_component_name = "form"
    flow = None
    action = None

    def get_required_permission(self):
        return get_permission_for_model(self.queryset.model, list(self.action.permissions_required)[0])

    def get_transition_func(self, flow, request):
        try:
            return getattr(flow, self.action.transition)
        except AttributeError:
            raise ImproperlyConfigured(
                f"{self.__class__.__name__} defines an action with an invalid tansition {self.action.transition} for workflow {self.flow.__name__}"
            )

    def get_object(self, **kwargs):
        """
        Return an object for editing. If no keyword arguments have been specified, this will be a new instance.
        """
        if not kwargs:
            # We're creating a new object
            return self.queryset.model()
        return super().get_object(**kwargs)

    def alter_object(self, obj, request, url_args, url_kwargs):
        """
        Provides a hook for views to modify an object before it is processed.

        Args:
            obj: The object being edited
            request: The current request
            url_args: URL path args
            url_kwargs: URL path kwargs
        """
        return obj

    #
    # Request handlers
    #

    def get(self, request, *args, **kwargs):
        """
        GET request handler.

        Args:
            request: The current request
        """
        obj = self.get_object(**kwargs)
        obj = self.alter_object(obj, request, args, kwargs)
        model = self.queryset.model

        initial_data = normalize_querydict(request.GET)
        form = self.form(instance=obj, initial=initial_data, user=request.user)

        restrict_form_fields(form, request.user)

        flow = self.flow(obj)

        # Ensure the workflow transition can proceed
        transition_func = self.get_transition_func(flow, request)
        if not transition_func.can_proceed():
            raise PermissionDenied
        if not transition_func.has_perm(request.user):
            raise PermissionDenied

        context = {
            "model": model,
            "object": obj,
            "form": form,
            "flow": flow,
            "action": self.action,
            **self.get_extra_context(request, obj),
        }

        # If the form is being displayed within a "modal" widget,
        # use the appropriate component
        if request.GET.get("_modal"):
            return HttpResponse(render_component(request, "modal.transition", context))

        # If this is an HTMX request, return only the rendered form HTML
        if htmx_partial(request):
            return HttpResponse(render_component(request, self.form_component_name, context))

        return render(
            request,
            self.template_name,
            {
                **context,
                "return_url": self.get_return_url(request, obj),
            },
        )

    def post(self, request, *args, **kwargs):
        """
        POST request handler.

        Args:
            request: The current request
        """
        logger = logging.getLogger("coldfront.views.ObjectFlowView")
        obj = self.get_object(**kwargs)
        model = self.queryset.model

        # Take a snapshot for change logging (if editing an existing object)
        if obj.pk and hasattr(obj, "snapshot"):
            obj.snapshot()

        obj = self.alter_object(obj, request, args, kwargs)

        form = self.form(data=request.POST, files=request.FILES, instance=obj, user=request.user)

        restrict_form_fields(form, request.user)

        flow = self.flow(obj)

        # Ensure the workflow transition can proceed
        transition_func = self.get_transition_func(flow, request)
        if not transition_func.can_proceed():
            raise PermissionDenied
        if not transition_func.has_perm(request.user):
            raise PermissionDenied

        if form.is_valid():
            logger.debug("Form validation was successful")

            try:
                with transaction.atomic(using=router.db_for_write(model)):
                    object_created = form.instance.pk is None
                    obj = form.save()

                    # Check that the new object conforms with any assigned object-level permissions
                    if not self.queryset.filter(pk=obj.pk).exists():
                        raise PermissionsViolation()

                # Perform the transition from the flow
                flow = self.flow(obj)
                transition_func()

                msg = "{} {}".format(
                    "Created" if object_created else "Modified", self.queryset.model._meta.verbose_name
                )
                logger.info(f"{msg} {obj} (PK: {obj.pk})")
                if hasattr(obj, "get_absolute_url"):
                    msg = format_html('{} <a href="{}">{}</a>', msg, obj.get_absolute_url(), escape(obj))
                else:
                    msg = f"{msg} {obj}"
                messages.success(request, msg)

                return_url = self.get_return_url(request, obj)

                #
                # If the object has been created or edited via HTMX, return an HTMX redirect to the object view
                if request.htmx:
                    return HttpResponse(
                        headers={
                            "HX-Location": return_url,
                        }
                    )

                return redirect(return_url)

            except (AbortRequest, PermissionsViolation) as e:
                logger.debug(e.message)
                form.add_error(None, e.message)

        else:
            logger.debug("Form validation failed")

        context = {
            "model": model,
            "object": obj,
            "form": form,
            "flow": flow,
            "action": self.action,
            "return_url": self.get_return_url(request, obj),
            **self.get_extra_context(request, obj),
        }

        # Form was submitted via a "modal" widget
        if "_modal" in request.POST:
            return HttpResponse(render_component(request, "modal.transition", context))

        return render(request, self.template_name, context)
