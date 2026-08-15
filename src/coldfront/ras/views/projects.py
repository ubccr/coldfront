# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from coldfront.forms import BulkDeleteForm
from coldfront.ras import filtersets, forms, tables
from coldfront.ras.models import Allocation, Project, ProjectUser
from coldfront.registry import register_model_view
from coldfront.users.permissions import get_permission_for_model
from coldfront.utils.query import count_related
from coldfront.views import ViewTab, generic
from coldfront.views.mixins import GetRelatedModelsMixin
from coldfront.views.object_actions import BulkDelete, BulkExport


def _sync_add_member(project, user):
    """If the project has a group FK set, add the user to it."""
    if project.group:
        project.group.add_member(user)


def _sync_remove_member(project, user):
    """If the project has a group FK set, remove the user from it."""
    if project.group:
        project.group.remove_member(user)


#
# Projects
#


@register_model_view(Project, "list", path="", detail=False)
class ProjectListView(generic.ObjectListView):
    queryset = Project.objects.annotate(
        user_count=count_related(ProjectUser, "project"),
        allocation_count=count_related(Allocation, "project"),
    )
    filterset = filtersets.ProjectFilterSet
    filterset_form = forms.ProjectFilterSetForm
    table = tables.ProjectTable


@register_model_view(Project)
class ProjectView(GetRelatedModelsMixin, generic.ObjectView):
    queryset = Project.objects.all()

    def get_extra_context(self, request, instance):
        return {
            "related_models": self.get_related_models(request, instance),
        }


@register_model_view(Project, "add", detail=False)
@register_model_view(Project, "edit")
class ProjectEditView(generic.ObjectEditView):
    queryset = Project.objects.all()
    form = forms.ProjectForm

    def alter_object(self, obj, request, url_args, url_kwargs):
        if not obj.pk:
            obj.owner = request.user

        return super().alter_object(obj, request, url_args, url_kwargs)


@register_model_view(Project, "delete")
class ProjectDeleteView(generic.ObjectDeleteView):
    queryset = Project.objects.all()


@register_model_view(Project, "bulk_import", path="import", detail=False)
class ProjectBulkImportView(generic.BulkImportView):
    queryset = Project.objects.all()
    model_form = forms.ProjectImportForm


@register_model_view(Project, "bulk_edit", path="edit", detail=False)
class ProjectBulkEditView(generic.BulkEditView):
    queryset = Project.objects.all()
    filterset = filtersets.ProjectFilterSet
    table = tables.ProjectTable
    form = forms.ProjectBulkEditForm


@register_model_view(Project, "bulk_delete", path="delete", detail=False)
class ProjectBulkDeleteView(generic.BulkDeleteView):
    queryset = Project.objects.all()
    filterset = filtersets.ProjectFilterSet
    table = tables.ProjectTable


@register_model_view(Project, "users")
class ProjectUserTabView(generic.ObjectChildrenView):
    actions = (BulkExport, BulkDelete)
    queryset = Project.objects.all()
    child_model = ProjectUser
    table = tables.ProjectUserTable
    filterset = filtersets.ProjectUserFilterSet
    filterset_form = forms.ProjectUserFilterSetForm
    template_name = "ras/project/users.html"
    tab = ViewTab(
        label=_("Users"),
        badge=lambda obj: obj.users.count(),
        permission="ras.view_project",
        weight=100,
    )

    def get_children(self, request, parent):
        return parent.users.restrict(request.user, "view")

    def get_table(self, *args, **kwargs):
        table = super().get_table(*args, **kwargs)
        # TODO: hide this column by default? add created?
        table.columns.hide("project")
        table.columns.show("created")
        return table


@register_model_view(Project, "allocations")
class ProjectAllocationTabView(generic.ObjectChildrenView):
    actions = (BulkExport, BulkDelete)
    queryset = Project.objects.all()
    child_model = Allocation
    table = tables.AllocationTable
    filterset = filtersets.AllocationFilterSet
    filterset_form = forms.AllocationFilterSetForm
    template_name = "ras/project/allocations.html"
    tab = ViewTab(
        label=_("Allocations"),
        badge=lambda obj: obj.allocations.count(),
        permission="ras.view_allocation",
        weight=200,
    )

    def get_children(self, request, parent):
        return parent.allocations.restrict(request.user, "view")


#
# Project bulk-unlink views: remove child records' links to the current project.
#


class ProjectBulkUnlinkView(generic.BulkDeleteView):
    """
    Base view for removing selected child records' links to the current project.

    Unlike ``BulkDeleteView``, which calls ``obj.delete()`` and destroys the global
    child instance, this view only removes the child objects from the current
    project's ``projects`` relation. The global record (and its links to other
    projects) is left untouched.

    Requires the custom ``unlink`` permission on the child model.
    """

    template_name = "ras/project/unlink.html"
    return_url_name = None
    child_relation = None

    def get_required_permission(self):
        return get_permission_for_model(self.queryset.model, "unlink")

    def get_queryset(self, request):
        self.project = get_object_or_404(Project, pk=request.resolver_match.kwargs["pk"])
        return self.queryset.model.objects.filter(projects=self.project)

    def get_return_url(self, request, obj=None):
        if request.GET.get("return_url") or request.POST.get("return_url"):
            return super().get_return_url(request, obj)
        return reverse(self.return_url_name, kwargs={"pk": self.project.pk})

    def post(self, request, **kwargs):
        model = self.queryset.model

        # Resolve the selected child objects. The queryset is already scoped to the
        # current project and restricted by the ``unlink`` permission.
        if request.POST.get("_all"):
            qs = self.queryset
            if self.filterset is not None:
                qs = self.filterset(request.GET, qs, request=request).qs
            pk_list = list(qs.only("pk").values_list("pk", flat=True))
        else:
            pk_list = [int(pk) for pk in request.POST.getlist("pk")]

        if "_confirm" in request.POST:
            form = BulkDeleteForm(model, request.POST)
            if form.is_valid():
                # Sever the links only; do not delete the child instances.
                queryset = self.queryset.filter(pk__in=pk_list)
                unlinked = queryset.count()
                getattr(self.project, self.child_relation).remove(*pk_list)

                msg = _("Removed {count} {object_type} from the project.").format(
                    count=unlinked,
                    object_type=model._meta.verbose_name_plural,
                )
                messages.success(request, msg)
                return redirect(self.get_return_url(request))
        else:
            form = BulkDeleteForm(
                model,
                initial={"pk": pk_list, "return_url": self.get_return_url(request)},
            )

        # Render the confirmation page listing the selected child objects.
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


#
# Project Users
#


@register_model_view(ProjectUser, "list", path="", detail=False)
class ProjectUserListView(generic.ObjectListView):
    queryset = ProjectUser.objects.all()
    filterset = filtersets.ProjectUserFilterSet
    filterset_form = forms.ProjectUserFilterSetForm
    table = tables.ProjectUserTable


@register_model_view(ProjectUser)
class ProjectUserView(generic.ObjectView):
    queryset = ProjectUser.objects.all()


@register_model_view(ProjectUser, "add", detail=False)
@register_model_view(ProjectUser, "edit")
class ProjectUserEditView(generic.ObjectEditView):
    queryset = ProjectUser.objects.all()
    form = forms.ProjectUserForm

    def alter_object(self, obj, request, url_args, url_kwargs):
        obj = super().alter_object(obj, request, url_args, url_kwargs)
        return obj

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        # Sync group membership after successful save
        obj = self.get_object(**kwargs)
        if obj.pk:
            _sync_add_member(obj.project, obj.user)
        return response


@register_model_view(ProjectUser, "delete")
class ProjectUserDeleteView(generic.ObjectDeleteView):
    queryset = ProjectUser.objects.all()

    def post(self, request, *args, **kwargs):
        obj = self.get_object(**kwargs)
        project = obj.project
        user = obj.user
        response = super().post(request, *args, **kwargs)
        _sync_remove_member(project, user)
        return response


@register_model_view(ProjectUser, "bulk_import", path="import", detail=False)
class ProjectUserBulkImportView(generic.BulkImportView):
    queryset = ProjectUser.objects.all()
    model_form = forms.ProjectUserImportForm

    def create_and_update_objects(self, form, request):
        saved_objects = super().create_and_update_objects(form, request)
        # Sync group membership for each newly created ProjectUser
        for pu in saved_objects:
            _sync_add_member(pu.project, pu.user)
        return saved_objects


@register_model_view(ProjectUser, "bulk_edit", path="edit", detail=False)
class ProjectUserBulkEditView(generic.BulkEditView):
    queryset = ProjectUser.objects.all()
    filterset = filtersets.ProjectUserFilterSet
    table = tables.ProjectUserTable
    form = forms.ProjectUserBulkEditForm


@register_model_view(ProjectUser, "bulk_delete", path="delete", detail=False)
class ProjectUserBulkDeleteView(generic.BulkDeleteView):
    queryset = ProjectUser.objects.all()
    filterset = filtersets.ProjectUserFilterSet
    table = tables.ProjectUserTable

    def post(self, request, **kwargs):
        # Collect project+user pairs before deletion
        deleted = []
        if request.POST.get("_all"):
            qs = self.queryset.model.objects.all()
            if self.filterset is not None:
                qs = self.filterset(request.GET, qs, request=request).qs
            pk_list = qs.only("pk").values_list("pk", flat=True)
        else:
            pk_list = [int(pk) for pk in request.POST.getlist("pk")]
        for pu in self.queryset.filter(pk__in=pk_list):
            deleted.append((pu.project, pu.user))
        response = super().post(request, **kwargs)
        for project, user in deleted:
            _sync_remove_member(project, user)
        return response
