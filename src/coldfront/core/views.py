# SPDX-FileCopyrightText: (C) DigitalOcean, LLC
# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.contenttypes.models import ContentType
from django.core.paginator import EmptyPage
from django.db.models import Count, Q
from django.http import Http404, HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views.generic import View
from django_cotton import render_component

from coldfront.registry import register_model_view
from coldfront.tables.paginator import EnhancedPaginator, get_paginate_count
from coldfront.users.models import User
from coldfront.utils.data import shallow_compare_dict
from coldfront.utils.query import count_related
from coldfront.views import generic
from coldfront.views.htmx import htmx_partial
from coldfront.views.object_actions import BulkDelete, BulkEdit, BulkExport, BulkImport, DeleteObject
from coldfront.views.utils import ViewTab, get_action_url

from . import (
    filtersets,
    forms,
    tables,
)
from .models import (
    CommentEntry,
    CustomField,
    CustomFieldChoiceSet,
    CustomLink,
    Job,
    ObjectChange,
    SavedFilter,
    TableConfig,
    Tag,
    TaggedItem,
)
from .plugins import get_local_plugins
from .tables import CatalogPluginTable, PluginVersionTable
from .templatetags.builtins.filters import render_markdown

#
# Saved Filter views
#


@register_model_view(SavedFilter, "list", path="", detail=False)
class SavedFilterListView(generic.ObjectListView):
    queryset = SavedFilter.objects.all()
    filterset = filtersets.SavedFilterFilterSet
    filterset_form = forms.SavedFilterFilterForm
    table = tables.SavedFilterTable
    actions = (BulkExport, BulkEdit, BulkDelete)


@register_model_view(SavedFilter)
class SavedFilterView(generic.ObjectView):
    queryset = SavedFilter.objects.all()

    def get_extra_context(self, request, instance):
        return {
            "parameters": instance.parameters,
        }


@register_model_view(SavedFilter, "add", detail=False)
@register_model_view(SavedFilter, "edit")
class SavedFilterEditView(generic.ObjectEditView):
    queryset = SavedFilter.objects.all()
    form = forms.SavedFilterForm

    def alter_object(self, obj, request, url_args, url_kwargs):
        if not obj.pk:
            obj.user = request.user
        return obj


@register_model_view(SavedFilter, "delete")
class SavedFilterDeleteView(generic.ObjectDeleteView):
    queryset = SavedFilter.objects.all()


@register_model_view(SavedFilter, "bulk_import", path="import", detail=False)
class SavedFilterBulkImportView(generic.BulkImportView):
    queryset = SavedFilter.objects.all()
    model_form = forms.SavedFilterImportForm


@register_model_view(SavedFilter, "bulk_edit", path="edit", detail=False)
class SavedFilterBulkEditView(generic.BulkEditView):
    queryset = SavedFilter.objects.all()
    filterset = filtersets.SavedFilterFilterSet
    table = tables.SavedFilterTable
    form = forms.SavedFilterBulkEditForm


@register_model_view(SavedFilter, "bulk_delete", path="delete", detail=False)
class SavedFilterBulkDeleteView(generic.BulkDeleteView):
    queryset = SavedFilter.objects.all()
    filterset = filtersets.SavedFilterFilterSet
    table = tables.SavedFilterTable


#
# Table Config views
#


@register_model_view(TableConfig, "list", path="", detail=False)
class TableConfigListView(generic.ObjectListView):
    queryset = TableConfig.objects.all()
    filterset = filtersets.TableConfigFilterSet
    filterset_form = forms.TableConfigFilterForm
    table = tables.TableConfigTable
    actions = (BulkExport, BulkEdit, BulkDelete)


@register_model_view(TableConfig)
class TableConfigView(generic.ObjectView):
    queryset = TableConfig.objects.all()

    def get_extra_context(self, request, instance):
        table = instance.table_class([])
        return {
            "columns": dict(table.columns.items()),
        }


@register_model_view(TableConfig, "add", detail=False)
@register_model_view(TableConfig, "edit")
class TableConfigEditView(generic.ObjectEditView):
    queryset = TableConfig.objects.all()
    form = forms.TableConfigForm
    template_name = "core/tableconfig_edit.html"

    def get(self, request, *args, **kwargs):
        # The add view requires the object_type & table parameters from the source table view
        if not kwargs and not (request.GET.get("object_type") and request.GET.get("table")):
            messages.warning(
                request,
                _("Table configurations must be created from an object list view."),
            )
            return redirect("home")

        return super().get(request, *args, **kwargs)

    def alter_object(self, obj, request, url_args, url_kwargs):
        if not obj.pk:
            obj.user = request.user
        return obj


@register_model_view(TableConfig, "delete")
class TableConfigDeleteView(generic.ObjectDeleteView):
    queryset = TableConfig.objects.all()


@register_model_view(TableConfig, "bulk_edit", path="edit", detail=False)
class TableConfigBulkEditView(generic.BulkEditView):
    queryset = TableConfig.objects.all()
    filterset = filtersets.TableConfigFilterSet
    table = tables.TableConfigTable
    form = forms.TableConfigBulkEditForm


@register_model_view(TableConfig, "bulk_delete", path="delete", detail=False)
class TableConfigBulkDeleteView(generic.BulkDeleteView):
    queryset = TableConfig.objects.all()
    filterset = filtersets.TableConfigFilterSet
    table = tables.TableConfigTable


# Job model views


@register_model_view(Job, "list", path="", detail=False)
class JobListView(generic.ObjectListView):
    queryset = Job.objects.all()
    filterset = filtersets.JobFilterSet
    filterset_form = forms.JobFilterForm
    table = tables.JobTable
    actions = (BulkExport, BulkDelete)


@register_model_view(Job)
class JobView(generic.ObjectView):
    queryset = Job.objects.all()
    actions = (DeleteObject,)


@register_model_view(Job, "log", path="log")
class JobLogView(generic.ObjectView):
    queryset = Job.objects.all()
    template_name = "core/job_log.html"
    actions = ()
    tab = ViewTab(
        label=_("Log"),
        permission="core.view_job",
        weight=500,
    )

    def get_extra_context(self, request, instance):
        return {
            "log_entries": instance.log_entries,
        }


@register_model_view(Job, "delete")
class JobDeleteView(generic.ObjectDeleteView):
    queryset = Job.objects.all()


@register_model_view(Job, "bulk_delete", path="delete", detail=False)
class JobBulkDeleteView(generic.BulkDeleteView):
    queryset = Job.objects.all()
    table = tables.JobTable
    filterset = filtersets.JobFilterSet


@register_model_view(Tag, "list", path="", detail=False)
class TagListView(generic.ObjectListView):
    queryset = Tag.objects.annotate(items=count_related(TaggedItem, "tag"))
    filterset = filtersets.TagFilterSet
    filterset_form = forms.TagFilterForm
    table = tables.TagTable


@register_model_view(Tag)
class TagView(generic.ObjectView):
    queryset = Tag.objects.all()

    def get_extra_context(self, request, instance):
        tagged_items = TaggedItem.objects.filter(tag=instance)
        taggeditem_table = tables.TaggedItemTable(data=tagged_items, orderable=False)
        taggeditem_table.configure(request)

        object_types = [
            {"content_type": ContentType.objects.get(pk=ti["content_type"]), "item_count": ti["item_count"]}
            for ti in tagged_items.values("content_type").annotate(item_count=Count("pk"))
        ]

        return {
            "taggeditem_table": taggeditem_table,
            "tagged_item_count": tagged_items.count(),
            "object_types": object_types,
        }


@register_model_view(Tag, "add", detail=False)
@register_model_view(Tag, "edit")
class TagEditView(generic.ObjectEditView):
    queryset = Tag.objects.all()
    form = forms.TagForm


@register_model_view(Tag, "delete")
class TagDeleteView(generic.ObjectDeleteView):
    queryset = Tag.objects.all()


@register_model_view(Tag, "bulk_import", path="import", detail=False)
class TagBulkImportView(generic.BulkImportView):
    queryset = Tag.objects.all()
    model_form = forms.TagImportForm


@register_model_view(Tag, "bulk_edit", path="edit", detail=False)
class TagBulkEditView(generic.BulkEditView):
    queryset = Tag.objects.all()
    filterset = filtersets.TagFilterSet
    table = tables.TagTable
    form = forms.TagBulkEditForm


@register_model_view(Tag, "bulk_delete", path="delete", detail=False)
class TagBulkDeleteView(generic.BulkDeleteView):
    queryset = Tag.objects.annotate(
        items=count_related(TaggedItem, "tag"),
    )
    table = tables.TagTable


#
# Change logging
#


@register_model_view(ObjectChange, "list", path="", detail=False)
class ObjectChangeListView(generic.ObjectListView):
    queryset = None
    filterset = filtersets.ObjectChangeFilterSet
    filterset_form = forms.ObjectChangeFilterForm
    table = tables.ObjectChangeTable
    template_name = "core/objectchange_list.html"
    actions = (BulkExport,)

    def get_queryset(self, request):
        return ObjectChange.objects.valid_models()


@register_model_view(ObjectChange)
class ObjectChangeView(generic.ObjectView):
    queryset = None

    def get_queryset(self, request):
        return ObjectChange.objects.valid_models()

    def get_extra_context(self, request, instance):
        related_changes = (
            ObjectChange.objects.valid_models()
            .restrict(request.user, "view")
            .filter(request_id=instance.request_id)
            .exclude(pk=instance.pk)
        )
        related_changes_table = tables.ObjectChangeTable(data=related_changes[:50], orderable=False)
        related_changes_table.configure(request)

        objectchanges = (
            ObjectChange.objects.valid_models()
            .restrict(request.user, "view")
            .filter(
                changed_object_type=instance.changed_object_type,
                changed_object_id=instance.changed_object_id,
            )
        )

        next_change = objectchanges.filter(time__gt=instance.time).order_by("time").first()
        prev_change = objectchanges.filter(time__lt=instance.time).order_by("-time").first()

        if not instance.prechange_data and instance.action in ["update", "delete"] and prev_change:
            non_atomic_change = True
            prechange_data = prev_change.postchange_data_clean
        else:
            non_atomic_change = False
            prechange_data = instance.prechange_data_clean

        if prechange_data and instance.postchange_data:
            diff_added = shallow_compare_dict(
                prechange_data or dict(),
                instance.postchange_data_clean or dict(),
                exclude=["last_updated"],
            )
            diff_removed = {x: prechange_data.get(x) for x in diff_added} if prechange_data else {}
        else:
            diff_added = None
            diff_removed = None

        return {
            "diff_added": diff_added,
            "diff_removed": diff_removed,
            "next_change": next_change,
            "prev_change": prev_change,
            "related_changes_table": related_changes_table,
            "related_changes_count": related_changes.count(),
            "non_atomic_change": non_atomic_change,
        }


#
# Custom field choices
#


@register_model_view(CustomFieldChoiceSet, "list", path="", detail=False)
class CustomFieldChoiceSetListView(generic.ObjectListView):
    queryset = CustomFieldChoiceSet.objects.all()
    filterset = filtersets.CustomFieldChoiceSetFilterSet
    filterset_form = forms.CustomFieldChoiceSetFilterForm
    table = tables.CustomFieldChoiceSetTable


@register_model_view(CustomFieldChoiceSet)
class CustomFieldChoiceSetView(generic.ObjectView):
    queryset = CustomFieldChoiceSet.objects.all()

    def get_extra_context(self, request, instance):

        # Paginate choices list
        per_page = get_paginate_count(request)
        try:
            page_number = request.GET.get("page", 1)
        except ValueError:
            page_number = 1
        paginator = EnhancedPaginator(instance.choices, per_page)
        try:
            choices = paginator.page(page_number)
        except EmptyPage:
            choices = paginator.page(paginator.num_pages)

        return {
            "paginator": paginator,
            "choices": choices,
        }


@register_model_view(CustomFieldChoiceSet, "add", detail=False)
@register_model_view(CustomFieldChoiceSet, "edit")
class CustomFieldChoiceSetEditView(generic.ObjectEditView):
    queryset = CustomFieldChoiceSet.objects.all()
    form = forms.CustomFieldChoiceSetForm


@register_model_view(CustomFieldChoiceSet, "delete")
class CustomFieldChoiceSetDeleteView(generic.ObjectDeleteView):
    queryset = CustomFieldChoiceSet.objects.all()


@register_model_view(CustomFieldChoiceSet, "bulk_import", path="import", detail=False)
class CustomFieldChoiceSetBulkImportView(generic.BulkImportView):
    queryset = CustomFieldChoiceSet.objects.all()
    model_form = forms.CustomFieldChoiceSetImportForm


@register_model_view(CustomFieldChoiceSet, "bulk_edit", path="edit", detail=False)
class CustomFieldChoiceSetBulkEditView(generic.BulkEditView):
    queryset = CustomFieldChoiceSet.objects.all()
    filterset = filtersets.CustomFieldChoiceSetFilterSet
    table = tables.CustomFieldChoiceSetTable
    form = forms.CustomFieldChoiceSetBulkEditForm


@register_model_view(CustomFieldChoiceSet, "bulk_delete", path="delete", detail=False)
class CustomFieldChoiceSetBulkDeleteView(generic.BulkDeleteView):
    queryset = CustomFieldChoiceSet.objects.all()
    filterset = filtersets.CustomFieldChoiceSetFilterSet
    table = tables.CustomFieldChoiceSetTable


#
# Custom fields
#


@register_model_view(CustomField, "list", path="", detail=False)
class CustomFieldListView(generic.ObjectListView):
    queryset = CustomField.objects.select_related("choice_set")
    filterset = filtersets.CustomFieldFilterSet
    filterset_form = forms.CustomFieldFilterForm
    table = tables.CustomFieldTable


@register_model_view(CustomField)
class CustomFieldView(generic.ObjectView):
    queryset = CustomField.objects.select_related("choice_set")

    def get_extra_context(self, request, instance):
        related_models = ()

        for object_type in instance.object_types.all():
            related_models += (
                object_type.model_class()
                .objects.restrict(request.user, "view")
                .exclude(
                    Q(**{f"custom_field_data__{instance.name}": ""})
                    | Q(**{f"custom_field_data__{instance.name}": None})
                ),
            )

        return {"related_models": related_models}


@register_model_view(CustomField, "add", detail=False)
@register_model_view(CustomField, "edit")
class CustomFieldEditView(generic.ObjectEditView):
    queryset = CustomField.objects.select_related("choice_set")
    form = forms.CustomFieldForm


@register_model_view(CustomField, "delete")
class CustomFieldDeleteView(generic.ObjectDeleteView):
    queryset = CustomField.objects.select_related("choice_set")


@register_model_view(CustomField, "bulk_import", path="import", detail=False)
class CustomFieldBulkImportView(generic.BulkImportView):
    queryset = CustomField.objects.select_related("choice_set")
    model_form = forms.CustomFieldImportForm


@register_model_view(CustomField, "bulk_edit", path="edit", detail=False)
class CustomFieldBulkEditView(generic.BulkEditView):
    queryset = CustomField.objects.all()
    filterset = filtersets.CustomFieldFilterSet
    table = tables.CustomFieldTable
    form = forms.CustomFieldBulkEditForm


@register_model_view(CustomField, "bulk_delete", path="delete", detail=False)
class CustomFieldBulkDeleteView(generic.BulkDeleteView):
    queryset = CustomField.objects.select_related("choice_set")
    filterset = filtersets.CustomFieldFilterSet
    table = tables.CustomFieldTable


#
# Plugins
#


class BasePluginView(UserPassesTestMixin, View):
    def test_func(self):
        return self.request.user.is_superuser

    def get_plugins(self, request):
        plugins = {}
        return get_local_plugins(plugins)


class PluginListView(BasePluginView):
    def get(self, request):
        q = request.GET.get("q", None)

        plugins = self.get_plugins(request).values()
        if q:
            plugins = [obj for obj in plugins if q.casefold() in obj.title_short.casefold()]

        plugins = [plugin for plugin in plugins if not plugin.hidden]

        table = CatalogPluginTable(plugins)
        table.configure(request)

        # If this is an HTMX request, return only the rendered table HTML
        if htmx_partial(request):
            return render_component(
                request,
                "table.htmx",
                table=table,
            )

        return render(
            request,
            "core/plugin_list.html",
            {
                "table": table,
            },
        )


class PluginView(BasePluginView):
    def get(self, request, name):

        plugins = self.get_plugins(request)
        if name not in plugins:
            raise Http404(_("Plugin {name} not found").format(name=name))
        plugin = plugins[name]

        table = PluginVersionTable(plugin.release_recent_history)
        table.configure(request)

        return render(
            request,
            "core/plugin.html",
            {
                "plugin": plugin,
                "table": table,
            },
        )


#
# Markdown
#


class RenderMarkdownView(LoginRequiredMixin, View):
    def post(self, request):
        form = forms.RenderMarkdownForm(request.POST)
        if not form.is_valid():
            HttpResponseBadRequest()
        rendered = render_markdown(form.cleaned_data["text"])

        return HttpResponse(rendered)


#
# Admin notification sending
#


class AdminNotificationSendView(UserPassesTestMixin, View):
    """
    View for superusers to send notifications to users.
    """

    template_name = "core/notification_send.html"

    def test_func(self):
        return self.request.user.is_superuser

    def get(self, request):
        form = forms.misc.AdminNotificationForm()
        return render(
            request,
            self.template_name,
            {
                "form": form,
            },
        )

    def post(self, request):
        form = forms.misc.AdminNotificationForm(data=request.POST)

        if form.is_valid():
            from generic_notifications import send_notification

            notification_type_key = form.cleaned_data["notification_type"]
            subject = form.cleaned_data["subject"]
            text = form.cleaned_data["text"]

            # Resolve the notification type class from the registry
            from generic_notifications.registry import registry as gn_registry

            nt_cls = gn_registry.get_type(notification_type_key)

            # Determine recipients
            recipients = set()

            if form.cleaned_data["notify_all"]:
                for user in User.objects.all():
                    recipients.add(user)
            else:
                for user in form.cleaned_data["users"]:
                    recipients.add(user)
                for group in form.cleaned_data["groups"]:
                    for user in group.user_set.all():
                        recipients.add(user)

            # Send notification to each recipient
            sent_count = 0
            for recipient in recipients:
                notification = send_notification(
                    recipient=recipient,
                    notification_type=nt_cls,
                    subject=subject,
                    text=text,
                )
                if notification:
                    sent_count += 1

            messages.success(
                request,
                _("Sent {count} notification(s) to {user_count} user(s).").format(
                    count=sent_count, user_count=len(recipients)
                ),
            )
            return redirect("core:notification_send")

        return render(
            request,
            self.template_name,
            {
                "form": form,
            },
        )


#
# Comment Entry views
#


@register_model_view(CommentEntry, "list", path="", detail=False)
class CommentEntryListView(generic.ObjectListView):
    queryset = CommentEntry.objects.all()
    filterset = filtersets.CommentEntryFilterSet
    filterset_form = forms.CommentEntryFilterForm
    table = tables.CommentEntryTable
    actions = (BulkImport, BulkEdit, BulkDelete)


@register_model_view(CommentEntry)
class CommentEntryView(generic.ObjectView):
    queryset = CommentEntry.objects.all()


@register_model_view(CommentEntry, "add", detail=False)
@register_model_view(CommentEntry, "edit")
class CommentEntryEditView(generic.ObjectEditView):
    queryset = CommentEntry.objects.all()
    form = forms.CommentEntryForm

    def alter_object(self, obj, request, args, kwargs):
        if not obj.pk:
            obj.created_by = request.user
        return obj

    def get_return_url(self, request, instance):
        if not instance.assigned_object:
            return reverse("core:commententry_list")
        obj = instance.assigned_object
        return get_action_url(obj, action="comments", kwargs={"pk": obj.pk})


@register_model_view(CommentEntry, "delete")
class CommentEntryDeleteView(generic.ObjectDeleteView):
    queryset = CommentEntry.objects.all()

    def get_return_url(self, request, instance):
        obj = instance.assigned_object
        return get_action_url(obj, action="comments", kwargs={"pk": obj.pk})


@register_model_view(CommentEntry, "bulk_import", path="import", detail=False)
class CommentEntryBulkImportView(generic.BulkImportView):
    queryset = CommentEntry.objects.all()
    model_form = forms.CommentEntryImportForm


@register_model_view(CommentEntry, "bulk_edit", path="edit", detail=False)
class CommentEntryBulkEditView(generic.BulkEditView):
    queryset = CommentEntry.objects.all()
    filterset = filtersets.CommentEntryFilterSet
    table = tables.CommentEntryTable
    form = forms.CommentEntryBulkEditForm


@register_model_view(CommentEntry, "bulk_delete", path="delete", detail=False)
class CommentEntryBulkDeleteView(generic.BulkDeleteView):
    queryset = CommentEntry.objects.all()
    filterset = filtersets.CommentEntryFilterSet
    table = tables.CommentEntryTable


class ObjectCommentsView(LoginRequiredMixin, View):
    """
    Show all comment entries for an object. The model class must be passed as a keyword argument when referencing this
    view in a URL path. For example:

        path("allocations/<int:pk>/comments/", ObjectCommentsView.as_view(), name="allocation_comments", kwargs={"model": Allocation}),

    Attributes:
        base_template: The name of the template to extend. If not provided, "{app}/{model}.html" will be used.
    """

    base_template = None
    tab = ViewTab(
        label=_("Comments"),
        badge=lambda obj: obj.comments.count(),
        permission="core.view_commententry",
        weight=9000,
    )

    def get(self, request, model, **kwargs):

        # Handle QuerySet restriction of parent object if needed
        if hasattr(model.objects, "restrict"):
            obj = get_object_or_404(model.objects.restrict(request.user, "view"), **kwargs)
        else:
            obj = get_object_or_404(model, **kwargs)

        # Gather all comments for this object
        content_type = ContentType.objects.get_for_model(model)
        commententries = (
            CommentEntry.objects.restrict(request.user, "view")
            .prefetch_related("created_by")
            .filter(
                assigned_object_type=content_type,
                assigned_object_id=obj.pk,
            )
        )
        commententry_table = tables.CommentEntryTable(commententries)
        commententry_table.configure(request)
        commententry_table.columns.hide("assigned_object_type")
        commententry_table.columns.hide("assigned_object")

        if request.user.has_perm("core.add_commententry"):
            form = forms.CommentEntryForm(
                user=request.user,
                initial={
                    "assigned_object_type": ContentType.objects.get_for_model(obj),
                    "assigned_object_id": obj.pk,
                },
            )
        else:
            form = None

        # Default to using "<app>/<model>.html" as the template, if it exists. Otherwise,
        # fall back to using base.html.
        if self.base_template is None:
            self.base_template = f"{model._meta.app_label}/{model._meta.model_name}.html"

        return render(
            request,
            "core/object_comments.html",
            {
                "object": obj,
                "form": form,
                "table": commententry_table,
                "base_template": self.base_template,
                "tab": self.tab,
            },
        )


#
# Custom Link views
#


@register_model_view(CustomLink, "list", path="", detail=False)
class CustomLinkListView(generic.ObjectListView):
    queryset = CustomLink.objects.all()
    filterset = filtersets.CustomLinkFilterSet
    filterset_form = forms.CustomLinkFilterForm
    table = tables.CustomLinkTable


@register_model_view(CustomLink)
class CustomLinkView(generic.ObjectView):
    queryset = CustomLink.objects.all()


@register_model_view(CustomLink, "add", detail=False)
@register_model_view(CustomLink, "edit")
class CustomLinkEditView(generic.ObjectEditView):
    queryset = CustomLink.objects.all()
    form = forms.CustomLinkForm


@register_model_view(CustomLink, "delete")
class CustomLinkDeleteView(generic.ObjectDeleteView):
    queryset = CustomLink.objects.all()


@register_model_view(CustomLink, "bulk_import", path="import", detail=False)
class CustomLinkBulkImportView(generic.BulkImportView):
    queryset = CustomLink.objects.all()
    model_form = forms.CustomLinkImportForm


@register_model_view(CustomLink, "bulk_edit", path="edit", detail=False)
class CustomLinkBulkEditView(generic.BulkEditView):
    queryset = CustomLink.objects.all()
    filterset = filtersets.CustomLinkFilterSet
    table = tables.CustomLinkTable
    form = forms.CustomLinkBulkEditForm


@register_model_view(CustomLink, "bulk_delete", path="delete", detail=False)
class CustomLinkBulkDeleteView(generic.BulkDeleteView):
    queryset = CustomLink.objects.all()
