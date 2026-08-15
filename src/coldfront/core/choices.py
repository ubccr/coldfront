# SPDX-FileCopyrightText: (C) DigitalOcean, LLC
# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django.utils.translation import gettext_lazy as _

from coldfront.choices import ChoiceSet
from coldfront.constants import CSV_DELIMITERS


class ObjectChangeActionChoices(ChoiceSet):
    ACTION_CREATE = "create"
    ACTION_UPDATE = "update"
    ACTION_DELETE = "delete"

    CHOICES = (
        (ACTION_CREATE, _("Created"), "success"),
        (ACTION_UPDATE, _("Updated"), "info"),
        (ACTION_DELETE, _("Deleted"), "danger"),
    )


class ColorChoices(ChoiceSet):
    COLOR_DARK_RED = "aa1409"
    COLOR_RED = "f44336"
    COLOR_PINK = "e91e63"
    COLOR_ROSE = "ffe4e1"
    COLOR_FUCHSIA = "ff66ff"
    COLOR_PURPLE = "9c27b0"
    COLOR_DARK_PURPLE = "673ab7"
    COLOR_INDIGO = "3f51b5"
    COLOR_BLUE = "2196f3"
    COLOR_LIGHT_BLUE = "03a9f4"
    COLOR_CYAN = "00bcd4"
    COLOR_TEAL = "009688"
    COLOR_AQUA = "00ffff"
    COLOR_DARK_GREEN = "2f6a31"
    COLOR_GREEN = "4caf50"
    COLOR_LIGHT_GREEN = "8bc34a"
    COLOR_LIME = "cddc39"
    COLOR_YELLOW = "ffeb3b"
    COLOR_AMBER = "ffc107"
    COLOR_ORANGE = "ff9800"
    COLOR_DARK_ORANGE = "ff5722"
    COLOR_BROWN = "795548"
    COLOR_LIGHT_GREY = "c0c0c0"
    COLOR_GREY = "9e9e9e"
    COLOR_DARK_GREY = "607d8b"
    COLOR_BLACK = "111111"
    COLOR_WHITE = "ffffff"

    CHOICES = (
        (COLOR_DARK_RED, _("Dark Red")),
        (COLOR_RED, _("Red")),
        (COLOR_PINK, _("Pink")),
        (COLOR_ROSE, _("Rose")),
        (COLOR_FUCHSIA, _("Fuchsia")),
        (COLOR_PURPLE, _("Purple")),
        (COLOR_DARK_PURPLE, _("Dark Purple")),
        (COLOR_INDIGO, _("Indigo")),
        (COLOR_BLUE, _("Blue")),
        (COLOR_LIGHT_BLUE, _("Light Blue")),
        (COLOR_CYAN, _("Cyan")),
        (COLOR_TEAL, _("Teal")),
        (COLOR_AQUA, _("Aqua")),
        (COLOR_DARK_GREEN, _("Dark Green")),
        (COLOR_GREEN, _("Green")),
        (COLOR_LIGHT_GREEN, _("Light Green")),
        (COLOR_LIME, _("Lime")),
        (COLOR_YELLOW, _("Yellow")),
        (COLOR_AMBER, _("Amber")),
        (COLOR_ORANGE, _("Orange")),
        (COLOR_DARK_ORANGE, _("Dark Orange")),
        (COLOR_BROWN, _("Brown")),
        (COLOR_LIGHT_GREY, _("Light Grey")),
        (COLOR_GREY, _("Grey")),
        (COLOR_DARK_GREY, _("Dark Grey")),
        (COLOR_BLACK, _("Black")),
        (COLOR_WHITE, _("White")),
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
        (ALWAYS, _("Always"), "green"),
        (IF_SET, _("If set"), "yellow"),
        (HIDDEN, _("Hidden"), "gray"),
    )


class CustomFieldUIEditableChoices(ChoiceSet):
    YES = "yes"
    NO = "no"
    HIDDEN = "hidden"

    CHOICES = (
        (YES, _("Yes"), "green"),
        (NO, _("No"), "red"),
        (HIDDEN, _("Hidden"), "gray"),
    )


#
# Button color choices
#


class ButtonColorChoices(ChoiceSet):
    DEFAULT = "default"
    BLUE = "blue"
    INDIGO = "indigo"
    PURPLE = "purple"
    PINK = "pink"
    RED = "red"
    ORANGE = "orange"
    YELLOW = "yellow"
    GREEN = "green"
    TEAL = "teal"
    CYAN = "cyan"
    GRAY = "gray"
    GREY = "gray"
    BLACK = "black"
    WHITE = "white"

    CHOICES = (
        (DEFAULT, _("Default")),
        (BLUE, _("Blue")),
        (INDIGO, _("Indigo")),
        (PURPLE, _("Purple")),
        (PINK, _("Pink")),
        (RED, _("Red")),
        (ORANGE, _("Orange")),
        (YELLOW, _("Yellow")),
        (GREEN, _("Green")),
        (TEAL, _("Teal")),
        (CYAN, _("Cyan")),
        (GRAY, _("Gray")),
        (BLACK, _("Black")),
        (WHITE, _("White")),
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
        (STATUS_PENDING, _("Pending"), "default"),
        (STATUS_SCHEDULED, _("Scheduled"), "info"),
        (STATUS_RUNNING, _("Running"), "warning"),
        (STATUS_COMPLETED, _("Completed"), "success"),
        (STATUS_FAILED, _("Failed"), "danger"),
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


class CustomLinkButtonClassChoices(ChoiceSet):
    key = "CustomLink.button_class"

    DEFAULT = "default"
    BLUE = "blue"
    INDIGO = "indigo"
    PURPLE = "purple"
    PINK = "pink"
    RED = "red"
    ORANGE = "orange"
    YELLOW = "yellow"
    GREEN = "green"
    TEAL = "teal"
    CYAN = "cyan"
    GRAY = "gray"
    GREY = "gray"
    BLACK = "black"
    WHITE = "white"
    LINK = "ghost-dark"

    CHOICES = list(
        (
            *ButtonColorChoices.CHOICES,
            (LINK, _("Link")),
        )
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
        (KIND_DANGER, _("Danger"), "danger"),
    ]
