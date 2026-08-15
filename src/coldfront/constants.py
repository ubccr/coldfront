# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

CORE_APPS = (
    "core",
    "users",
    "tenancy",
    "ras",
    "account",
    "slurm",
    "storage",
)

CUSTOMFIELD_EMPTY_VALUES = (None, "", [])

# Redis lock keys for job scheduling (used by ``enqueue_once()`` and
# ``JobRunner.handle()`` to prevent duplicate periodic job schedules).
# Must be unique across all Redis lock consumers.
LOCK_KEYS = {
    "job-schedules": "coldfront.job-schedules",
}

HTML_ALLOWED_TAGS = {
    "a",
    "b",
    "blockquote",
    "br",
    "code",
    "dd",
    "del",
    "div",
    "dl",
    "dt",
    "em",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "hr",
    "i",
    "img",
    "li",
    "ol",
    "p",
    "pre",
    "strong",
    "table",
    "tbody",
    "td",
    "th",
    "thead",
    "tr",
    "ul",
}


HTML_ALLOWED_ATTRIBUTES = {
    "a": {"href", "title"},
    "div": {"class"},
    "h1": {"id"},
    "h2": {"id"},
    "h3": {"id"},
    "h4": {"id"},
    "h5": {"id"},
    "h6": {"id"},
    "img": {"alt", "src", "title"},
    "td": {"align"},
    "th": {"align"},
}

# Boolean widget choices
BOOLEAN_WITH_BLANK_CHOICES = (
    ("", "---------"),
    ("True", "Yes"),
    ("False", "No"),
)

#
# CSV-style format delimiters
#
CSV_DELIMITERS = {
    "comma": ",",
    "semicolon": ";",
    "pipe": "|",
    "tab": "\t",
}
