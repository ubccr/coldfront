# SPDX-FileCopyrightText: (C) DigitalOcean, LLC
# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django.db.models import Count

from coldfront.core.models import ObjectChange
from coldfront.core.tables import ObjectChangeTable
from coldfront.registry import register_model_view
from coldfront.views import generic

from . import filtersets, forms, tables
from .models import Group, ObjectPermission, Role, Token, User

#
# Users
#


@register_model_view(User, "list", path="", detail=False)
class UserListView(generic.ObjectListView):
    queryset = User.objects.all()
    filterset = filtersets.UserFilterSet
    filterset_form = forms.UserFilterSetForm
    table = tables.UserTable


@register_model_view(User)
class UserView(generic.ObjectView):
    queryset = User.objects.all()
    template_name = "users/user.html"

    def get_extra_context(self, request, instance):
        changelog = ObjectChange.objects.valid_models().restrict(request.user, "view").filter(user=instance)[:20]
        changelog_table = ObjectChangeTable(changelog)
        changelog_table.orderable = False
        changelog_table.configure(request)

        return {
            "changelog_table": changelog_table,
        }


@register_model_view(User, "add", detail=False)
@register_model_view(User, "edit")
class UserEditView(generic.ObjectEditView):
    queryset = User.objects.all()
    form = forms.UserForm


@register_model_view(User, "delete")
class UserDeleteView(generic.ObjectDeleteView):
    queryset = User.objects.all()


@register_model_view(User, "bulk_import", path="import", detail=False)
class UserBulkImportView(generic.BulkImportView):
    queryset = User.objects.all()
    model_form = forms.UserImportForm


@register_model_view(User, "bulk_edit", path="edit", detail=False)
class UserBulkEditView(generic.BulkEditView):
    queryset = User.objects.all()
    filterset = filtersets.UserFilterSet
    table = tables.UserTable
    form = forms.UserBulkEditForm

    def post_save_operations(self, form, obj):
        if form.cleaned_data.get("add_groups", None):
            obj.groups.add(*form.cleaned_data["add_groups"])
        if form.cleaned_data.get("remove_groups", None):
            obj.groups.remove(*form.cleaned_data["remove_groups"])


@register_model_view(User, "bulk_delete", path="delete", detail=False)
class UserBulkDeleteView(generic.BulkDeleteView):
    queryset = User.objects.all()
    filterset = filtersets.UserFilterSet
    table = tables.UserTable


#
# Groups
#


@register_model_view(Group, "list", path="", detail=False)
class GroupListView(generic.ObjectListView):
    queryset = Group.objects.annotate(users_count=Count("user")).order_by("name")
    filterset = filtersets.GroupFilterSet
    filterset_form = forms.GroupFilterSetForm
    table = tables.GroupTable


@register_model_view(Group)
class GroupView(generic.ObjectView):
    queryset = Group.objects.all()
    template_name = "users/group.html"


@register_model_view(Group, "add", detail=False)
@register_model_view(Group, "edit")
class GroupEditView(generic.ObjectEditView):
    queryset = Group.objects.all()
    form = forms.GroupForm


@register_model_view(Group, "delete")
class GroupDeleteView(generic.ObjectDeleteView):
    queryset = Group.objects.all()


@register_model_view(Group, "bulk_import", path="import", detail=False)
class GroupBulkImportView(generic.BulkImportView):
    queryset = Group.objects.all()
    model_form = forms.GroupImportForm


@register_model_view(Group, "bulk_edit", path="edit", detail=False)
class GroupBulkEditView(generic.BulkEditView):
    queryset = Group.objects.all()
    filterset = filtersets.GroupFilterSet
    table = tables.GroupTable
    form = forms.GroupBulkEditForm

    def post_save_operations(self, form, obj):
        pass


@register_model_view(Group, "bulk_delete", path="delete", detail=False)
class GroupBulkDeleteView(generic.BulkDeleteView):
    queryset = Group.objects.annotate(users_count=Count("user")).order_by("name")
    filterset = filtersets.GroupFilterSet
    table = tables.GroupTable


#
# Roles
#


@register_model_view(Role, "list", path="", detail=False)
class RoleListView(generic.ObjectListView):
    queryset = Role.objects.all()
    filterset = filtersets.RoleFilterSet
    filterset_form = forms.RoleFilterSetForm
    table = tables.RoleTable


@register_model_view(Role)
class RoleView(generic.ObjectView):
    queryset = Role.objects.all()
    template_name = "users/role.html"


@register_model_view(Role, "add", detail=False)
@register_model_view(Role, "edit")
class RoleEditView(generic.ObjectEditView):
    queryset = Role.objects.all()
    form = forms.RoleForm


@register_model_view(Role, "delete")
class RoleDeleteView(generic.ObjectDeleteView):
    queryset = Role.objects.all()


@register_model_view(Role, "bulk_import", path="import", detail=False)
class RoleBulkImportView(generic.BulkImportView):
    queryset = Role.objects.all()
    model_form = forms.RoleImportForm


@register_model_view(Role, "bulk_edit", path="edit", detail=False)
class RoleBulkEditView(generic.BulkEditView):
    queryset = Role.objects.all()
    filterset = filtersets.RoleFilterSet
    table = tables.RoleTable
    form = forms.RoleBulkEditForm

    def post_save_operations(self, form, obj):
        pass


@register_model_view(Role, "bulk_delete", path="delete", detail=False)
class RoleBulkDeleteView(generic.BulkDeleteView):
    queryset = Role.objects.all()
    filterset = filtersets.RoleFilterSet
    table = tables.RoleTable


#
# ObjectPermissions
#


@register_model_view(ObjectPermission, "list", path="", detail=False)
class ObjectPermissionListView(generic.ObjectListView):
    queryset = ObjectPermission.objects.all()
    filterset = filtersets.ObjectPermissionFilterSet
    filterset_form = forms.ObjectPermissionFilterSetForm
    table = tables.ObjectPermissionTable


@register_model_view(ObjectPermission)
class ObjectPermissionView(generic.ObjectView):
    queryset = ObjectPermission.objects.all()
    template_name = "users/objectpermission.html"


@register_model_view(ObjectPermission, "add", detail=False)
@register_model_view(ObjectPermission, "edit")
class ObjectPermissionEditView(generic.ObjectEditView):
    queryset = ObjectPermission.objects.all()
    form = forms.ObjectPermissionForm


@register_model_view(ObjectPermission, "delete")
class ObjectPermissionDeleteView(generic.ObjectDeleteView):
    queryset = ObjectPermission.objects.all()
    filterset = filtersets.ObjectPermissionFilterSet


@register_model_view(ObjectPermission, "bulk_edit", path="edit", detail=False)
class ObjectPermissionBulkEditView(generic.BulkEditView):
    queryset = ObjectPermission.objects.all()
    filterset = filtersets.ObjectPermissionFilterSet
    table = tables.ObjectPermissionTable
    form = forms.ObjectPermissionBulkEditForm

    def post_save_operations(self, form, obj):
        pass


@register_model_view(ObjectPermission, "bulk_delete", path="delete", detail=False)
class ObjectPermissionBulkDeleteView(generic.BulkDeleteView):
    queryset = ObjectPermission.objects.all()
    filterset = filtersets.ObjectPermissionFilterSet
    table = tables.ObjectPermissionTable


#
# Tokens
#


@register_model_view(Token, "list", path="", detail=False)
class TokenListView(generic.ObjectListView):
    queryset = Token.objects.all()
    filterset = filtersets.TokenFilterSet
    filterset_form = forms.TokenFilterSetForm
    table = tables.TokenTable


@register_model_view(Token)
class TokenView(generic.ObjectView):
    queryset = Token.objects.all()


@register_model_view(Token, "add", detail=False)
@register_model_view(Token, "edit")
class TokenEditView(generic.ObjectEditView):
    queryset = Token.objects.all()
    form = forms.TokenForm
    template_name = "users/token_edit.html"


@register_model_view(Token, "delete")
class TokenDeleteView(generic.ObjectDeleteView):
    queryset = Token.objects.all()


@register_model_view(Token, "bulk_import", path="import", detail=False)
class TokenBulkImportView(generic.BulkImportView):
    queryset = Token.objects.all()
    model_form = forms.TokenImportForm


@register_model_view(Token, "bulk_edit", path="edit", detail=False)
class TokenBulkEditView(generic.BulkEditView):
    queryset = Token.objects.all()
    table = tables.TokenTable
    form = forms.TokenBulkEditForm

    def post_save_operations(self, form, obj):
        pass


@register_model_view(Token, "bulk_delete", path="delete", detail=False)
class TokenBulkDeleteView(generic.BulkDeleteView):
    queryset = Token.objects.all()
    table = tables.TokenTable
