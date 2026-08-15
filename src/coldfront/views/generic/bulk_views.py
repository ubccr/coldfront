# SPDX-FileCopyrightText: (C) DigitalOcean, LLC
# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

import logging
from collections import Counter

from django.contrib import messages
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRel
from django.core.exceptions import FieldDoesNotExist, ImproperlyConfigured, ObjectDoesNotExist, ValidationError
from django.db import router, transaction
from django.db.models import ManyToManyField, ManyToManyRel, ProtectedError, RestrictedError
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.utils.safestring import mark_safe
from django.utils.translation import gettext as _
from django_cotton import render_component
from django_tables2.export import TableExport
from mptt.models import MPTTModel

from coldfront.core.choices import CustomFieldUIEditableChoices
from coldfront.core.models import CustomField
from coldfront.exceptions import AbortRequest, PermissionsViolation
from coldfront.forms import BulkDeleteForm, BulkImportForm
from coldfront.models.features import ChangeLoggingMixin
from coldfront.tables import get_table_configs
from coldfront.users.permissions import get_permission_for_model
from coldfront.utils.forms import restrict_form_fields
from coldfront.utils.query import reapply_model_ordering
from coldfront.utils.request import safe_for_redirect
from coldfront.utils.strings import title
from coldfront.views import get_action_url, handle_protectederror
from coldfront.views.htmx import htmx_partial
from coldfront.views.mixins import GetReturnURLMixin
from coldfront.views.object_actions import AddObject, BulkDelete, BulkEdit, BulkExport, BulkImport

from .base import BaseMultiObjectView
from .mixins import ActionsMixin, TableMixin


class ObjectListView(BaseMultiObjectView, ActionsMixin, TableMixin):
    """
    Display multiple objects, all the same type, as a table.

    Attributes:
        filterset: A django-filter FilterSet that is applied to the queryset
        filterset_form: The form class used to render filter options
        actions: An iterable of ObjectAction subclasses (see ActionsMixin)
    """

    template_name = "generic/object_list.html"
    filterset = None
    filterset_form = None
    # actions = (AddObject, BulkImport, BulkExport, BulkEdit, BulkRename, BulkDelete)
    actions = (AddObject, BulkImport, BulkExport, BulkEdit, BulkDelete)

    def get_required_permission(self):
        return get_permission_for_model(self.queryset.model, "view")

    #
    # Export methods
    #

    def export_yaml(self):
        """
        Export the queryset of objects as concatenated YAML documents.
        """
        yaml_data = [obj.to_yaml() for obj in self.queryset]

        return "---\n".join(yaml_data)

    def export_table(self, table, columns=None, filename=None, delimiter=None):
        """
        Export all table data in CSV format.

        Args:
            table: The Table instance to export
            columns: A list of specific columns to include. If None, all columns will be exported.
            filename: The name of the file attachment sent to the client. If None, will be determined automatically
                from the queryset model name.
            delimiter: The character used to separate columns (a comma is used by default)
        """
        exclude_columns = {"pk", "actions"}
        if columns:
            all_columns = [col_name for col_name, _ in table.selected_columns + table.available_columns]
            exclude_columns.update({col for col in all_columns if col not in columns})
        exporter = TableExport(
            export_format=TableExport.CSV,
            table=table,
            exclude_columns=exclude_columns,
        )
        return exporter.response(filename=filename or f"coldfront_{self.queryset.model._meta.verbose_name_plural}.csv")

    #
    # Request handlers
    #

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return reapply_model_ordering(qs)

    def get(self, request):
        """
        GET request handler.

        Args:
            request: The current request
        """
        model = self.queryset.model

        if self.filterset:
            self.queryset = self.filterset(request.GET, self.queryset, request=request).qs

        # Determine the available actions
        actions = self.get_permitted_actions(request.user)
        has_table_actions = any(action.multi for action in actions)

        if "export" in request.GET:
            # Export the current table view
            if request.GET["export"] == "table":
                table = self.get_table(self.queryset, request, has_table_actions)
                columns = [name for name, _ in table.selected_columns]
                return self.export_table(table, columns)

            # Check for YAML export support on the model
            elif hasattr(model, "to_yaml"):
                response = HttpResponse(self.export_yaml(), content_type="text/yaml")
                filename = "coldfront_{}.yaml".format(self.queryset.model._meta.verbose_name_plural)
                response["Content-Disposition"] = 'attachment; filename="{}"'.format(filename)
                return response

            # Fall back to default table/YAML export
            else:
                table = self.get_table(self.queryset, request, has_table_actions)
                return self.export_table(table)

        # Render the objects table
        table = self.get_table(self.queryset, request, has_table_actions)

        # If this is an HTMX request, return only the rendered table HTML
        if htmx_partial(request):
            if request.GET.get("embedded", False):
                table.embedded = True
                # Hide selection checkboxes
                if "pk" in table.base_columns:
                    table.columns.hide("pk")
            return HttpResponse(
                render_component(
                    request,
                    "table.htmx",
                    table=table,
                    actions=actions,
                    model=model,
                )
            )

        filter_form = self.filterset_form(request.GET) if self.filterset_form else None
        if filter_form:
            restrict_form_fields(filter_form, request.user)

        context = {
            "model": model,
            "table": table,
            "table_configs": get_table_configs(table, request.user),
            "actions": actions,
            "filter_form": filter_form,
            "prerequisite_model": self.get_prerequisite_model(),
            **self.get_extra_context(request),
        }

        return render(request, self.template_name, context)


class BulkImportView(GetReturnURLMixin, BaseMultiObjectView):
    """
    Import objects in bulk (CSV/JSON/YAML format).

    Attributes:
        model_form: The form used to create each imported object
    """

    template_name = "generic/bulk_import.html"
    model_form = None
    related_object_forms = dict()

    def get_required_permission(self):
        return get_permission_for_model(self.queryset.model, "add")

    def prep_related_object_data(self, parent, data):
        """
        Hook to modify the data for related objects before it's passed to the related object form (for example, to
        assign a parent object).
        """
        return data

    def _get_form_fields(self):
        form = self.model_form()
        required_fields = {}
        optional_fields = {}

        # Return only visible fields, with required fields listed first
        for field in form.visible_fields():
            if field.is_hidden:
                continue
            if field.field.required:
                required_fields[field.name] = field.field
            else:
                optional_fields[field.name] = field.field

        return {**required_fields, **optional_fields}

    def _compile_form_errors(self, errors, index, prefix=None):
        error_messages = []
        for field_name, errors in errors.items():
            prefix = f"{prefix}." if prefix else ""
            if field_name == "__all__":
                field_name = ""
            for err in errors:
                error_messages.append(f"Record {index} {prefix}{field_name}: {err}")
        return error_messages

    def _save_object(self, model_form, request, parent_idx):
        _action = "Updated" if model_form.instance.pk else "Created"

        # Save the primary object
        obj = self.save_object(model_form, request)

        # Enforce object-level permissions
        if not self.queryset.filter(pk=obj.pk).first():
            raise PermissionsViolation()

        # Iterate through the related object forms (if any), validating and saving each instance.
        for field_name, related_object_form in self.related_object_forms.items():
            related_objects = model_form.data.get(field_name, list())
            if not isinstance(related_objects, list):
                raise ValidationError(self._compile_form_errors({field_name: [_("Must be a list.")]}, index=parent_idx))

            related_obj_pks = []
            for i, rel_obj_data in enumerate(related_objects, start=1):
                if not isinstance(rel_obj_data, dict):
                    raise ValidationError(
                        self._compile_form_errors(
                            {f"{field_name}[{i}]": [_("Must be a dictionary.")]},
                            index=parent_idx,
                        )
                    )

                rel_obj_data = self.prep_related_object_data(obj, rel_obj_data)
                f = related_object_form(rel_obj_data)

                for subfield_name, field in f.fields.items():
                    if subfield_name not in rel_obj_data and hasattr(field, "initial"):
                        f.data[subfield_name] = field.initial

                if f.is_valid():
                    related_obj = f.save()
                    related_obj_pks.append(related_obj.pk)
                else:
                    # Replicate errors on the related object form to the import form for display and abort
                    raise ValidationError(
                        self._compile_form_errors(f.errors, index=parent_idx, prefix=f"{field_name}[{i}]")
                    )

            # Enforce object-level permissions on related objects
            model = related_object_form.Meta.model
            if model.objects.filter(pk__in=related_obj_pks).count() != len(related_obj_pks):
                raise ObjectDoesNotExist

        return obj

    def save_object(self, object_form, request):
        """
        Provide a hook to modify the object immediately before saving it (e.g. to encrypt secret data).

        Args:
            object_form: The model form instance
            request: The current request
        """
        return object_form.save()

    def _process_import_records(self, form, request, records, prefetched_objects):
        """
        Process CSV import records and save objects.
        """
        saved_objects = []

        for i, record in enumerate(records, start=1):
            object_id = int(record.pop("id")) if record.get("id") else None

            # Determine whether this object is being created or updated
            if object_id:
                try:
                    instance = prefetched_objects[object_id]
                except KeyError:
                    raise ValidationError(
                        self._compile_form_errors(
                            {"id": [_("Object with ID {id} does not exist").format(id=object_id)]}, index=i
                        )
                    )

                # Take a snapshot for change logging
                if instance.pk and hasattr(instance, "snapshot"):
                    instance.snapshot()

            else:
                instance = self.queryset.model()

                # For newly created objects, apply any default values for custom fields
                for cf in CustomField.objects.get_for_model(self.queryset.model):
                    if cf.ui_editable != CustomFieldUIEditableChoices.YES:
                        # Skip custom fields which are not editable via the UI
                        continue
                    field_name = f"cf_{cf.name}"
                    if field_name not in record:
                        record[field_name] = cf.default

            # Record changelog message (if any)
            instance._changelog_message = form.cleaned_data.get("changelog_message", "")

            # Instantiate the model form for the object
            model_form_kwargs = {
                "data": record,
                "instance": instance,
            }
            if hasattr(form, "_csv_headers"):
                model_form_kwargs["headers"] = form._csv_headers  # Add CSV headers
            model_form = self.model_form(**model_form_kwargs)

            # When updating, omit all form fields other than those specified in the record. (No
            # fields are required when modifying an existing object.)
            if object_id:
                unused_fields = [f for f in model_form.fields if f not in record]
                for field_name in unused_fields:
                    del model_form.fields[field_name]

            restrict_form_fields(model_form, request.user)

            if model_form.is_valid():
                obj = self._save_object(model_form, request, i)
                saved_objects.append(obj)
            else:
                # Raise model form errors
                raise ValidationError(self._compile_form_errors(model_form.errors, index=i))

        return saved_objects

    def create_and_update_objects(self, form, request):
        records = list(form.cleaned_data["data"])

        # Prefetch objects to be updated, if any
        prefetch_ids = [int(record["id"]) for record in records if record.get("id")]

        # check for duplicate IDs
        duplicate_pks = [pk for pk, count in Counter(prefetch_ids).items() if count > 1]
        if duplicate_pks:
            error_msg = _("Duplicate objects found: {model} with ID(s) {ids} appears multiple times").format(
                model=title(self.queryset.model._meta.verbose_name),
                ids=", ".join(str(pk) for pk in sorted(duplicate_pks)),
            )
            raise ValidationError(error_msg)

        prefetched_objects = (
            {obj.pk: obj for obj in self.queryset.model.objects.filter(id__in=prefetch_ids)} if prefetch_ids else {}
        )

        # For MPTT models, delay tree updates until all saves are complete
        if issubclass(self.queryset.model, MPTTModel):
            with self.queryset.model.objects.delay_mptt_updates():
                saved_objects = self._process_import_records(form, request, records, prefetched_objects)
        else:
            saved_objects = self._process_import_records(form, request, records, prefetched_objects)

        return saved_objects

    #
    # Request handlers
    #

    def get(self, request):
        model = self.model_form._meta.model
        form = BulkImportForm()
        if not issubclass(model, ChangeLoggingMixin):
            form.fields.pop("changelog_message")

        return render(
            request,
            self.template_name,
            {
                "model": model,
                "form": form,
                "fields": self._get_form_fields(),
                "return_url": self.get_return_url(request),
                **self.get_extra_context(request),
            },
        )

    def post(self, request):
        logger = logging.getLogger("coldfront.views.BulkImportView")
        model = self.model_form._meta.model
        form = BulkImportForm(request.POST, request.FILES)
        if not issubclass(model, ChangeLoggingMixin):
            form.fields.pop("changelog_message")

        if form.is_valid():
            logger.debug("Import form validation was successful")

            redirect_url = get_action_url(model, action="list")
            return_url = request.GET.get("return_url") or request.POST.get("return_url")
            if return_url and safe_for_redirect(return_url):
                redirect_url = return_url

            try:
                # Iterate through data and bind each record to a new model form instance.
                with transaction.atomic(using=router.db_for_write(model)):
                    new_objects = self.create_and_update_objects(form, request)

                    # Enforce object-level permissions
                    if self.queryset.filter(pk__in=[obj.pk for obj in new_objects]).count() != len(new_objects):
                        raise PermissionsViolation

                msg = _("Imported {count} {object_type}").format(
                    count=len(new_objects), object_type=model._meta.verbose_name_plural
                )
                logger.info(msg)

                messages.success(request, msg)
                return redirect(f"{redirect_url}?modified_by_request={request.id}")

            except (AbortRequest, PermissionsViolation, ValidationError) as e:
                err_messages = e.messages if type(e) is ValidationError else [e.message]
                for msg in err_messages:
                    logger.debug(msg)
                    form.add_error(None, msg)

        else:
            logger.debug("Form validation failed")

        return render(
            request,
            self.template_name,
            {
                "model": model,
                "form": form,
                "fields": self._get_form_fields(),
                "return_url": self.get_return_url(request),
                **self.get_extra_context(request),
            },
        )


class BulkDeleteView(GetReturnURLMixin, BaseMultiObjectView):
    """
    Delete objects in bulk.

    Attributes:
        filterset: FilterSet to apply when deleting by QuerySet
        table: The table used to display objects being deleted
    """

    template_name = "generic/bulk_delete.html"
    filterset = None
    table = None

    def get_required_permission(self):
        return get_permission_for_model(self.queryset.model, "delete")

    #
    # Request handlers
    #

    def get(self, request):
        return redirect(self.get_return_url(request))

    def post(self, request, **kwargs):
        logger = logging.getLogger("coldfront.views.BulkDeleteView")
        model = self.queryset.model

        # Are we deleting *all* objects in the queryset or just a selected subset?
        if request.POST.get("_all"):
            qs = model.objects.all()
            if self.filterset is not None:
                qs = self.filterset(request.GET, qs, request=request).qs
            pk_list = qs.only("pk").values_list("pk", flat=True)
        else:
            pk_list = [int(pk) for pk in request.POST.getlist("pk")]

        if "_confirm" in request.POST:
            form = BulkDeleteForm(model, request.POST)
            if form.is_valid():
                logger.debug("Form validation was successful")

                # Delete objects
                queryset = self.queryset.filter(pk__in=pk_list)
                deleted_count = queryset.count()
                try:
                    with transaction.atomic(using=router.db_for_write(model)):
                        for obj in queryset:
                            # Take a snapshot of change-logged models
                            if hasattr(obj, "snapshot"):
                                obj.snapshot()

                            # Attach the changelog message (if any) to the object
                            obj._changelog_message = form.cleaned_data.get("changelog_message")

                            # Delete the object
                            obj.delete()

                    msg = _("Deleted {count} {object_type}").format(
                        count=deleted_count, object_type=model._meta.verbose_name_plural
                    )
                    logger.info(msg)

                    messages.success(request, msg)

                except (ProtectedError, RestrictedError) as e:
                    logger.warning(f"Caught {type(e)} while attempting to delete objects")
                    handle_protectederror(queryset, request, e)

                except AbortRequest as e:
                    logger.debug(e.message)
                    messages.error(request, mark_safe(e.message))

                return redirect(self.get_return_url(request))

            logger.debug("Form validation failed")

        else:
            form = BulkDeleteForm(
                model,
                initial={
                    "pk": pk_list,
                    "return_url": self.get_return_url(request),
                },
            )

        # Retrieve objects being deleted
        table = self.table(self.queryset.filter(pk__in=pk_list), orderable=False)
        if not table.rows:
            messages.warning(
                request, _("No {object_type} were selected.").format(object_type=model._meta.verbose_name_plural)
            )
            return redirect(self.get_return_url(request))

        return render(
            request,
            self.template_name,
            {
                "model": model,
                "form": form,
                "table": table,
                "return_url": self.get_return_url(request),
                **self.get_extra_context(request),
            },
        )


class BulkEditView(GetReturnURLMixin, BaseMultiObjectView):
    """
    Edit objects in bulk.

    Attributes:
        filterset: FilterSet to apply when editing by QuerySet
        form: The form class used to edit objects in bulk
    """

    template_name = "generic/bulk_edit.html"
    filterset = None
    form = None

    def get_required_permission(self):
        return get_permission_for_model(self.queryset.model, "change")

    def post_save_operations(self, form, obj):
        """
        This method is called for each object in _update_objects. Override to perform additional object-level
        operations that are specific to a particular ModelForm.
        """
        # Add/remove tags
        if form.cleaned_data.get("add_tags", None):
            obj.tags.add(*form.cleaned_data["add_tags"])
        if form.cleaned_data.get("remove_tags", None):
            obj.tags.remove(*form.cleaned_data["remove_tags"])

    def _update_objects(self, form, request):
        custom_fields = getattr(form, "custom_fields", {})
        standard_fields = [field for field in form.fields if field not in list(custom_fields) + ["pk"]]
        nullified_fields = request.POST.getlist("_nullify")
        updated_objects = []
        model_fields = {}
        m2m_fields = {}

        # Build list of model fields and m2m fields for later iteration
        for name in standard_fields:
            try:
                model_field = self.queryset.model._meta.get_field(name)
                if isinstance(model_field, (ManyToManyField, ManyToManyRel)):
                    m2m_fields[name] = model_field
                elif isinstance(model_field, GenericRel):
                    # Ignore generic relations (these may be used for other purposes in the form)
                    continue
                else:
                    model_fields[name] = model_field
            except FieldDoesNotExist:
                # This form field is used to modify a field rather than set its value directly
                model_fields[name] = None

        for obj in self.queryset.filter(pk__in=form.cleaned_data["pk"]):
            # Take a snapshot of change-logged models
            if hasattr(obj, "snapshot"):
                obj.snapshot()

            # Attach the changelog message (if any) to the object
            obj._changelog_message = form.cleaned_data.get("changelog_message")

            # Update standard fields. If a field is listed in _nullify, delete its value.
            for name, model_field in model_fields.items():
                # Handle nullification
                if name in form.nullable_fields and name in nullified_fields:
                    if type(model_field) is GenericForeignKey:
                        setattr(obj, name, None)
                    else:
                        setattr(obj, name, None if model_field.null else "")
                # Normal fields
                elif name in form.changed_data:
                    setattr(obj, name, form.cleaned_data[name])

            # Update custom fields
            for name, customfield in custom_fields.items():
                if not name.startswith("cf_"):
                    raise ImproperlyConfigured(
                        _("Custom field form field name must begin with 'cf_': {name}").format(name=name)
                    )
                cf_name = name[3:]  # Strip cf_ prefix
                if name in form.nullable_fields and name in nullified_fields:
                    obj.custom_field_data[cf_name] = None
                elif name in form.changed_data:
                    obj.custom_field_data[cf_name] = customfield.serialize(form.cleaned_data[name])

            # Store M2M values for validation
            obj._m2m_values = {}
            for field in obj._meta.local_many_to_many:
                if value := form.cleaned_data.get(field.name):
                    obj._m2m_values[field.name] = list(value)
                elif field.name in nullified_fields:
                    obj._m2m_values[field.name] = []

            obj.full_clean()
            obj.save()
            updated_objects.append(obj)

            # Handle M2M fields after save
            for name, m2m_field in m2m_fields.items():
                if name in form.nullable_fields and name in nullified_fields:
                    getattr(obj, name).clear()
                elif form.cleaned_data[name]:
                    getattr(obj, name).set(form.cleaned_data[name])

            self.post_save_operations(form, obj)

        # Rebuild the tree for MPTT models
        if issubclass(self.queryset.model, MPTTModel):
            self.queryset.model.objects.rebuild()

        return updated_objects

    #
    # Request handlers
    #

    def get(self, request):
        return redirect(self.get_return_url(request))

    def post(self, request, **kwargs):
        logger = logging.getLogger("coldfront.views.BulkEditView")
        model = self.queryset.model

        # If we are editing *all* objects in the queryset, replace the PK list with all matched objects.
        if request.POST.get("_all") and self.filterset is not None:
            pk_list = self.filterset(request.GET, self.queryset.values_list("pk", flat=True), request=request).qs
        else:
            pk_list = request.POST.getlist("pk")

        # Include the PK list as initial data for the form
        initial_data = {"pk": pk_list}

        # Check for other contextual data needed for the form. We avoid passing all of request.GET because the
        # filter values will conflict with the bulk edit form fields.
        # TODO: Find a better way to accomplish this
        if "device" in request.GET:
            initial_data["device"] = request.GET.get("device")
        elif "device_type" in request.GET:
            initial_data["device_type"] = request.GET.get("device_type")
        elif "virtual_machine" in request.GET:
            initial_data["virtual_machine"] = request.GET.get("virtual_machine")

        post_data = request.POST.copy()
        post_data.setlist("pk", pk_list)
        form = self.form(post_data, initial=initial_data)
        restrict_form_fields(form, request.user)

        if "_apply" in request.POST:
            if form.is_valid():
                logger.debug("Form validation was successful")

                try:
                    with transaction.atomic(using=router.db_for_write(model)):
                        updated_objects = self._update_objects(form, request)

                        # Enforce object-level permissions
                        object_count = self.queryset.filter(pk__in=[obj.pk for obj in updated_objects]).count()
                        if object_count != len(updated_objects):
                            raise PermissionsViolation

                    msg = _("Updated {count} {object_type}").format(
                        count=len(updated_objects),
                        object_type=model._meta.verbose_name_plural,
                    )
                    logger.info(msg)

                    messages.success(self.request, msg)
                    return redirect(self.get_return_url(request))

                except (AbortRequest, PermissionsViolation, ValidationError) as e:
                    err_messages = e.messages if type(e) is ValidationError else [e.message]
                    for msg in err_messages:
                        logger.debug(msg)
                        form.add_error(None, msg)

            else:
                logger.debug("Form validation failed")

        # Retrieve objects being edited
        table = self.table(self.queryset.filter(pk__in=pk_list), orderable=False)
        if not table.rows:
            messages.warning(
                request,
                _("No {object_type} were selected.").format(object_type=model._meta.verbose_name_plural),
            )
            return redirect(self.get_return_url(request))

        return render(
            request,
            self.template_name,
            {
                "model": model,
                "form": form,
                "table": table,
                "return_url": self.get_return_url(request),
                **self.get_extra_context(request),
            },
        )
