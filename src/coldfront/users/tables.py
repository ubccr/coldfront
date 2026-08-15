# SPDX-FileCopyrightText: (C) DigitalOcean, LLC
# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

import django_tables2 as tables
from django.utils.translation import gettext as _

from coldfront.tables import ColdFrontTable, columns

from .models import Group, ObjectPermission, Role, Token, User

__all__ = (
    "GroupTable",
    "ObjectPermissionTable",
    "UserTable",
    "TokenTable",
)


class UserTable(ColdFrontTable):
    username = tables.Column(verbose_name=_("Username"), linkify=True)
    groups = columns.ManyToManyColumn(verbose_name=_("Groups"), linkify_item=("users:group", {"pk": tables.A("pk")}))
    is_active = columns.BooleanColumn(
        verbose_name=_("Is Active"),
    )
    is_superuser = columns.BooleanColumn(
        verbose_name=_("Is Superuser"),
    )
    actions = columns.ActionsColumn(
        actions=("edit", "delete"),
    )

    class Meta(ColdFrontTable.Meta):
        model = User
        fields = (
            "pk",
            "id",
            "username",
            "first_name",
            "last_name",
            "email",
            "groups",
            "is_active",
            "is_superuser",
            "last_login",
        )
        default_columns = ("pk", "username", "first_name", "last_name", "email", "is_active")


class GroupTable(ColdFrontTable):
    name = tables.Column(verbose_name=_("Name"), linkify=True)
    actions = columns.ActionsColumn(
        actions=("edit", "delete"),
    )

    class Meta(ColdFrontTable.Meta):
        model = Group
        fields = ("pk", "id", "name", "users_count", "description")


class RoleTable(ColdFrontTable):
    name = tables.Column(verbose_name=_("Name"), linkify=True)
    weight = tables.Column(verbose_name=_("Weight"))
    users = columns.ManyToManyColumn(
        verbose_name=_("Users"),
        linkify_item=("users:user", {"pk": tables.A("pk")}),
    )
    groups = columns.ManyToManyColumn(
        verbose_name=_("Groups"),
        linkify_item=("users:group", {"pk": tables.A("pk")}),
    )
    permissions = columns.ManyToManyColumn(
        verbose_name=_("Permissions"),
        linkify_item=("users:objectpermission", {"pk": tables.A("pk")}),
        accessor=tables.A("object_permissions"),
    )
    actions = columns.ActionsColumn(
        actions=("edit", "delete"),
    )

    class Meta(ColdFrontTable.Meta):
        model = Role
        fields = (
            "pk",
            "id",
            "name",
            "weight",
            "description",
            "users",
            "groups",
            "object_permissions",
        )
        default_columns = (
            "pk",
            "name",
            "weight",
            "description",
            "users",
            "groups",
        )


class ObjectPermissionTable(ColdFrontTable):
    name = tables.Column(verbose_name=_("Name"), linkify=True)
    object_types = columns.ContentTypesColumn(
        verbose_name=_("Object Types"),
    )
    enabled = columns.BooleanColumn(
        verbose_name=_("Enabled"),
    )
    can_view = columns.BooleanColumn(
        verbose_name=_("Can View"),
        orderable=False,
    )
    can_add = columns.BooleanColumn(
        verbose_name=_("Can Add"),
        orderable=False,
    )
    can_change = columns.BooleanColumn(
        verbose_name=_("Can Change"),
        orderable=False,
    )
    can_delete = columns.BooleanColumn(
        verbose_name=_("Can Delete"),
        orderable=False,
    )
    custom_actions = columns.ArrayColumn(
        verbose_name=_("Custom Actions"),
        accessor=tables.A("actions"),
    )
    users = columns.ManyToManyColumn(
        verbose_name=_("Users"),
        linkify_item=("users:user", {"pk": tables.A("pk")}),
    )
    groups = columns.ManyToManyColumn(
        verbose_name=_("Groups"),
        linkify_item=("users:group", {"pk": tables.A("pk")}),
    )
    actions = columns.ActionsColumn(
        actions=("edit", "delete"),
    )

    class Meta(ColdFrontTable.Meta):
        model = ObjectPermission
        fields = (
            "pk",
            "id",
            "name",
            "enabled",
            "object_types",
            "can_view",
            "can_add",
            "can_change",
            "can_delete",
            "custom_actions",
            "users",
            "groups",
            "constraints",
            "description",
        )
        default_columns = (
            "pk",
            "name",
            "enabled",
            "object_types",
            "can_view",
            "can_add",
            "can_change",
            "can_delete",
            "description",
        )


TOKEN = """<samp><a href="{{ record.get_absolute_url }}">{{ record }}</a></samp>"""


class TokenTable(ColdFrontTable):
    user = tables.Column(linkify=True, verbose_name=_("User"))
    token = columns.TemplateColumn(
        verbose_name=_("Token"),
        template_code=TOKEN,
        orderable=False,
    )
    enabled = columns.BooleanColumn(verbose_name=_("Enabled"))
    write_enabled = columns.BooleanColumn(verbose_name=_("Write Enabled"))
    created = columns.DateTimeColumn(
        timespec="minutes",
        verbose_name=_("Created"),
    )
    expires = columns.DateTimeColumn(
        timespec="minutes",
        verbose_name=_("Expires"),
    )
    last_used = columns.DateTimeColumn(
        verbose_name=_("Last Used"),
    )
    actions = columns.ActionsColumn(
        actions=("edit", "delete"),
    )

    class Meta(ColdFrontTable.Meta):
        model = Token
        fields = (
            "pk",
            "id",
            "token",
            "pepper_id",
            "user",
            "description",
            "enabled",
            "write_enabled",
            "created",
            "expires",
            "last_used",
        )
        default_columns = (
            "token",
            "user",
            "enabled",
            "write_enabled",
            "description",
        )
