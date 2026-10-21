# SPDX-FileCopyrightText: (C) DigitalOcean, LLC
# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django.utils.translation import gettext_lazy as _

from coldfront.lib.choices import ChoiceSet
from coldfront.lib.constants import CSV_DELIMITERS


class ObjectChangeActionChoices(ChoiceSet):
    ACTION_CREATE = "create"
    ACTION_UPDATE = "update"
    ACTION_DELETE = "delete"

    CHOICES = (
        (ACTION_CREATE, _("Created"), "success"),
        (ACTION_UPDATE, _("Updated"), "info"),
        (ACTION_DELETE, _("Deleted"), "error"),
    )


class ColorChoices(ChoiceSet):
    PRIMARY = "primary"
    SECONDARY = "secondary"
    ACCENT = "accent"
    NEUTRAL = "neutral"
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"

    CHOICES = (
        (PRIMARY, _("Primary")),
        (SECONDARY, _("Secondary")),
        (ACCENT, _("Accent")),
        (NEUTRAL, _("Neutral")),
        (INFO, _("Info")),
        (SUCCESS, _("Success")),
        (WARNING, _("Warning")),
        (ERROR, _("Error")),
    )


class CustomFieldTypeChoices(ChoiceSet):
    TYPE_TEXT = "text"
    TYPE_LONGTEXT = "longtext"
    TYPE_INTEGER = "integer"
    TYPE_DECIMAL = "decimal"
    TYPE_BOOLEAN = "boolean"
    TYPE_DATE = "date"
    TYPE_DATETIME = "datetime"
    TYPE_SELECT = "select"
    TYPE_MULTISELECT = "multiselect"
    TYPE_OBJECT = "object"
    TYPE_MULTIOBJECT = "multiobject"

    CHOICES = (
        (TYPE_TEXT, _("Text")),
        (TYPE_LONGTEXT, _("Text (long)")),
        (TYPE_INTEGER, _("Integer")),
        (TYPE_DECIMAL, _("Decimal")),
        (TYPE_BOOLEAN, _("Boolean (true/false)")),
        (TYPE_DATE, _("Date")),
        (TYPE_DATETIME, _("Date & time")),
        (TYPE_SELECT, _("Selection")),
        (TYPE_MULTISELECT, _("Multiple selection")),
        (TYPE_OBJECT, _("Object")),
        (TYPE_MULTIOBJECT, _("Multiple objects")),
    )


class CustomFieldFilterLogicChoices(ChoiceSet):
    FILTER_DISABLED = "disabled"
    FILTER_LOOSE = "loose"
    FILTER_EXACT = "exact"

    CHOICES = (
        (FILTER_DISABLED, _("Disabled")),
        (FILTER_LOOSE, _("Loose")),
        (FILTER_EXACT, _("Exact")),
    )


class CustomFieldUIVisibleChoices(ChoiceSet):
    ALWAYS = "always"
    IF_SET = "if-set"
    HIDDEN = "hidden"

    CHOICES = (
        (ALWAYS, _("Always"), "success"),
        (IF_SET, _("If set"), "warning"),
        (HIDDEN, _("Hidden"), "neutral"),
    )


class CustomFieldUIEditableChoices(ChoiceSet):
    YES = "yes"
    NO = "no"
    HIDDEN = "hidden"

    CHOICES = (
        (YES, _("Yes"), "success"),
        (NO, _("No"), "error"),
        (HIDDEN, _("Hidden"), "neutral"),
    )


class CSVDelimiterChoices(ChoiceSet):
    AUTO = "auto"
    COMMA = CSV_DELIMITERS["comma"]
    SEMICOLON = CSV_DELIMITERS["semicolon"]
    PIPE = CSV_DELIMITERS["pipe"]
    TAB = CSV_DELIMITERS["tab"]

    CHOICES = [
        (AUTO, _("Auto-detect")),
        (COMMA, _("Comma")),
        (SEMICOLON, _("Semicolon")),
        (PIPE, _("Pipe")),
        (TAB, _("Tab")),
    ]


class ImportMethodChoices(ChoiceSet):
    DIRECT = "direct"
    UPLOAD = "upload"

    CHOICES = [
        (DIRECT, _("Direct")),
        (UPLOAD, _("Upload")),
    ]


class ImportFormatChoices(ChoiceSet):
    AUTO = "auto"
    CSV = "csv"
    JSON = "json"
    YAML = "yaml"

    CHOICES = [
        (AUTO, _("Auto-detect")),
        (CSV, "CSV"),
        (JSON, "JSON"),
        (YAML, "YAML"),
    ]


class JobStatusChoices(ChoiceSet):
    STATUS_PENDING = "pending"
    STATUS_SCHEDULED = "scheduled"
    STATUS_RUNNING = "running"
    STATUS_COMPLETED = "completed"
    STATUS_FAILED = "failed"
    STATUS_ERRORED = "errored"

    CHOICES = (
        (STATUS_PENDING, _("Pending"), "neutral"),
        (STATUS_SCHEDULED, _("Scheduled"), "info"),
        (STATUS_RUNNING, _("Running"), "warning"),
        (STATUS_COMPLETED, _("Completed"), "success"),
        (STATUS_FAILED, _("Failed"), "error"),
        (STATUS_ERRORED, _("Errored"), "secondary"),
    )

    # States that are considered "enqueued" — waiting for or currently executing
    ENQUEUED_STATE_CHOICES = (
        STATUS_PENDING,
        STATUS_SCHEDULED,
        STATUS_RUNNING,
    )

    # States that are terminal — job has finished
    TERMINAL_STATE_CHOICES = (
        STATUS_COMPLETED,
        STATUS_FAILED,
        STATUS_ERRORED,
    )


class JobNotificationChoices(ChoiceSet):
    NOTIFICATION_ALWAYS = "always"
    NOTIFICATION_ON_FAILURE = "on_failure"
    NOTIFICATION_NEVER = "never"

    CHOICES = (
        (NOTIFICATION_ALWAYS, _("Always")),
        (NOTIFICATION_ON_FAILURE, _("On failure")),
        (NOTIFICATION_NEVER, _("Never")),
    )


class CommentKindChoices(ChoiceSet):
    key = "CommentEntry.kind"

    KIND_INFO = "info"
    KIND_SUCCESS = "success"
    KIND_WARNING = "warning"
    KIND_DANGER = "danger"

    CHOICES = [
        (KIND_INFO, _("Info"), "info"),
        (KIND_SUCCESS, _("Success"), "success"),
        (KIND_WARNING, _("Warning"), "warning"),
        (KIND_DANGER, _("Danger"), "error"),
    ]
