# SPDX-FileCopyrightText: (C) DigitalOcean, LLC
# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

import re

__all__ = (
    "enum_key",
    "title",
)


def title(value):
    """
    Improved implementation of str.title(); retains all existing uppercase letters.
    """
    return " ".join([w[0].upper() + w[1:] for w in str(value).split()])


def enum_key(value):
    """
    Convert the given value to a string suitable for use as an Enum key.
    """
    value = str(value).upper()
    return re.sub(r"[^_A-Z0-9]", "_", value)
