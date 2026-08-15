# SPDX-FileCopyrightText: (C) DigitalOcean, LLC
# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

import json

import django_tables2 as tables
from django.utils.translation import gettext_lazy as _

from coldfront.core.models import (
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
from coldfront.tables import ColdFrontTable, columns

from .template_code import OBJECTCHANGE_FULL_NAME, OBJECTCHANGE_OBJECT, OBJECTCHANGE_REQUEST_ID


class TagTable(ColdFrontTable):
    name = tables.Column(verbose_name=_("Name"), linkify=True)
    color = columns.ColorColumn(
        verbose_name=_("Color"),
    )
    object_types = columns.ContentTypesColumn(
        verbose_name=_("Object Types"),
    )
    owner = tables.Column(linkify=True, verbose_name=_("Owner"))

    class Meta(ColdFrontTable.Meta):
        model = Tag
        fields = (
            "pk",
            "id",
            "name",
            "items",
            "slug",
            "color",
            "weight",
            "description",
            "object_types",
            "created",
            "last_updated",
            "actions",
        )
        default_columns = ("pk", "name", "items", "slug", "color", "description")


class TaggedItemTable(ColdFrontTable):
    id = tables.Column(
        verbose_name=_("ID"),
        linkify=lambda record: record.content_object.get_absolute_url(),
        accessor="content_object__id",
    )
    content_type = columns.ContentTypeColumn(verbose_name=_("Type"))
    content_object = tables.Column(linkify=True, orderable=False, verbose_name=_("Object"))
    actions = columns.ActionsColumn(actions=())

    class Meta(ColdFrontTable.Meta):
        model = TaggedItem
        fields = ("id", "content_type", "content_object")


class ObjectChangeTable(ColdFrontTable):
    time = columns.DateTimeColumn(verbose_name=_("Time"), timespec="minutes", linkify=True)
    user_name = tables.Column(verbose_name=_("Username"))
    full_name = tables.TemplateColumn(
        accessor=tables.A("user"), template_code=OBJECTCHANGE_FULL_NAME, verbose_name=_("Full Name"), orderable=False
    )
    action = columns.ChoiceFieldColumn(
        verbose_name=_("Action"),
    )
    changed_object_type = columns.ContentTypeColumn(verbose_name=_("Type"))
    object_repr = tables.TemplateColumn(
        accessor=tables.A("changed_object"),
        template_code=OBJECTCHANGE_OBJECT,
        verbose_name=_("Object"),
        orderable=False,
    )
    request_id = tables.TemplateColumn(template_code=OBJECTCHANGE_REQUEST_ID, verbose_name=_("Request ID"))
    message = tables.Column(
        verbose_name=_("Message"),
    )
    actions = columns.ActionsColumn(actions=())

    class Meta(ColdFrontTable.Meta):
        model = ObjectChange
        fields = (
            "pk",
            "time",
            "user_name",
            "full_name",
            "action",
            "changed_object_type",
            "object_repr",
            "request_id",
            "message",
            "actions",
        )
        default_columns = (
            "pk",
            "time",
            "user_name",
            "action",
            "changed_object_type",
            "object_repr",
            "message",
            "actions",
        )


class CustomFieldChoiceSetTable(ColdFrontTable):
    name = tables.Column(
        verbose_name=_("Name"),
        linkify=True,
    )
    choices = tables.TemplateColumn(
        template_code="""{% for v in value %}{{ v|split:":"|last }}{% if not forloop.last %}, {% endif %}{% endfor %}"""
    )
    choice_count = tables.TemplateColumn(
        accessor=tables.A("choices"),
        template_code="{{ value|length }}",
        orderable=False,
        verbose_name=_("Count"),
    )
    order_alphabetically = columns.BooleanColumn(
        verbose_name=_("Order Alphabetically"),
        false_mark=None,
    )

    class Meta(ColdFrontTable.Meta):
        model = CustomFieldChoiceSet
        fields = (
            "pk",
            "id",
            "name",
            "description",
            "choice_count",
            "choices",
            "order_alphabetically",
            "created",
            "last_updated",
        )
        default_columns = ("pk", "name", "choices", "choice_count", "description")


class CustomFieldTable(ColdFrontTable):
    name = tables.Column(
        verbose_name=_("Name"),
        linkify=True,
    )
    object_types = columns.ContentTypesColumn(
        verbose_name=_("Object Types"),
    )
    required = columns.BooleanColumn(
        verbose_name=_("Required"),
        false_mark=None,
    )
    unique = columns.BooleanColumn(
        verbose_name=_("Validate Uniqueness"),
        false_mark=None,
    )
    ui_visible = columns.ChoiceFieldColumn(
        verbose_name=_("Visible"),
    )
    ui_editable = columns.ChoiceFieldColumn(
        verbose_name=_("Editable"),
    )
    description = columns.MarkdownColumn(
        verbose_name=_("Description"),
    )
    related_object_type = columns.ContentTypeColumn(
        verbose_name=_("Related Object Type"),
    )
    choice_set = tables.Column(
        linkify=True,
        verbose_name=_("Choice Set"),
    )
    choices = columns.ChoicesColumn(
        max_items=10,
        orderable=False,
        verbose_name=_("Choices"),
    )
    is_cloneable = columns.BooleanColumn(
        verbose_name=_("Is Cloneable"),
        false_mark=None,
    )
    validation_minimum = tables.Column(
        verbose_name=_("Minimum Value"),
    )
    validation_maximum = tables.Column(
        verbose_name=_("Maximum Value"),
    )
    validation_regex = tables.Column(
        verbose_name=_("Validation Regex"),
    )
    owner = tables.Column(linkify=True, verbose_name=_("Owner"))

    class Meta(ColdFrontTable.Meta):
        model = CustomField
        fields = (
            "pk",
            "id",
            "name",
            "object_types",
            "label",
            "type",
            "related_object_type",
            "group_name",
            "required",
            "unique",
            "default",
            "description",
            "search_weight",
            "filter_logic",
            "ui_visible",
            "ui_editable",
            "is_cloneable",
            "weight",
            "choice_set",
            "choices",
            "validation_minimum",
            "validation_maximum",
            "validation_regex",
            "comments",
            "created",
            "last_updated",
        )
        default_columns = (
            "pk",
            "name",
            "object_types",
            "label",
            "group_name",
            "type",
            "required",
            "unique",
            "description",
        )


class JobTable(ColdFrontTable):
    name = tables.Column(
        verbose_name=_("Name"),
        linkify=True,
    )
    status = columns.ChoiceFieldColumn(
        verbose_name=_("Status"),
    )
    created = columns.DateTimeColumn(
        verbose_name=_("Created"),
        timespec="minutes",
    )
    started = columns.DateTimeColumn(
        verbose_name=_("Started"),
        timespec="minutes",
    )
    completed = columns.DateTimeColumn(
        verbose_name=_("Completed"),
        timespec="minutes",
    )
    user = tables.Column(
        verbose_name=_("User"),
        linkify=True,
    )
    interval = tables.Column(
        verbose_name=_("Interval"),
    )
    actions = columns.ActionsColumn(actions=())

    class Meta(ColdFrontTable.Meta):
        model = Job
        fields = (
            "pk",
            "id",
            "name",
            "status",
            "created",
            "started",
            "completed",
            "user",
            "interval",
            "error",
            "queue_name",
            "actions",
        )
        default_columns = (
            "pk",
            "name",
            "status",
            "created",
            "started",
            "completed",
            "interval",
        )


class SavedFilterTable(ColdFrontTable):
    name = tables.Column(
        verbose_name=_("Name"),
        linkify=True,
    )
    object_types = columns.ContentTypesColumn(
        verbose_name=_("Object Types"),
    )
    enabled = columns.BooleanColumn(
        verbose_name=_("Enabled"),
    )
    shared = columns.BooleanColumn(
        verbose_name=_("Shared"),
        false_mark=None,
    )
    parameters = tables.TemplateColumn(
        template_code="""{{ value|json }}""",
        verbose_name=_("Parameters"),
    )

    def value_parameters(self, value):
        return json.dumps(value)

    class Meta(ColdFrontTable.Meta):
        model = SavedFilter
        fields = (
            "pk",
            "id",
            "name",
            "slug",
            "object_types",
            "description",
            "user",
            "weight",
            "enabled",
            "shared",
            "parameters",
            "created",
            "last_updated",
        )
        default_columns = (
            "pk",
            "name",
            "object_types",
            "user",
            "description",
            "enabled",
            "shared",
        )


class CustomLinkTable(ColdFrontTable):
    name = tables.Column(
        verbose_name=_("Name"),
        linkify=True,
    )
    object_types = columns.ContentTypesColumn(
        verbose_name=_("Object Types"),
    )
    enabled = columns.BooleanColumn(
        verbose_name=_("Enabled"),
    )
    new_window = columns.BooleanColumn(
        verbose_name=_("New Window"),
        false_mark=None,
    )

    class Meta(ColdFrontTable.Meta):
        model = CustomLink
        fields = (
            "pk",
            "id",
            "name",
            "object_types",
            "enabled",
            "link_text",
            "link_url",
            "weight",
            "group_name",
            "button_class",
            "new_window",
            "created",
            "last_updated",
        )
        default_columns = (
            "pk",
            "name",
            "object_types",
            "enabled",
            "group_name",
            "button_class",
            "new_window",
        )


class CommentEntryTable(ColdFrontTable):
    created = columns.DateTimeColumn(
        verbose_name=_("Created"),
        timespec="minutes",
        linkify=True,
    )
    assigned_object_type = columns.ContentTypeColumn(
        verbose_name=_("Object Type"),
    )
    assigned_object = tables.Column(
        linkify=True,
        orderable=False,
        verbose_name=_("Object"),
    )
    kind = columns.ChoiceFieldColumn(
        verbose_name=_("Kind"),
    )
    comments = columns.MarkdownColumn(
        verbose_name=_("Comments"),
    )
    comments_short = tables.TemplateColumn(
        accessor=tables.A("comments"),
        template_code="{{ value|markdown|truncatewords_html:50 }}",
        verbose_name=_("Comments (Short)"),
    )
    created_by = tables.Column(
        verbose_name=_("Created By"),
        linkify=True,
    )
    tags = columns.TagColumn(
        url_name="core:commententry_list",
    )

    class Meta(ColdFrontTable.Meta):
        model = CommentEntry
        fields = (
            "pk",
            "id",
            "created",
            "assigned_object_type",
            "assigned_object",
            "kind",
            "comments",
            "comments_short",
            "created_by",
            "tags",
            "actions",
        )
        default_columns = (
            "pk",
            "created",
            "assigned_object_type",
            "kind",
            "comments_short",
            "created_by",
            "tags",
        )


class TableConfigTable(ColdFrontTable):
    name = tables.Column(
        verbose_name=_("Name"),
        linkify=True,
    )
    object_type = columns.ContentTypeColumn(
        verbose_name=_("Object Type"),
    )
    table = tables.Column(
        verbose_name=_("Table Name"),
    )
    enabled = columns.BooleanColumn(
        verbose_name=_("Enabled"),
    )
    shared = columns.BooleanColumn(
        verbose_name=_("Shared"),
        false_mark=None,
    )

    class Meta(ColdFrontTable.Meta):
        model = TableConfig
        fields = (
            "pk",
            "id",
            "name",
            "object_type",
            "table",
            "description",
            "user",
            "weight",
            "enabled",
            "shared",
            "created",
            "last_updated",
        )
        default_columns = (
            "pk",
            "name",
            "object_type",
            "table",
            "user",
            "description",
            "enabled",
            "shared",
        )
