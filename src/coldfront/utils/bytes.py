# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

import re
from collections import namedtuple

#
# This code was adopted from https://github.com/xolox/python-humanfriendly/blob/master/humanfriendly/__init__.py#L198
#

SizeUnit = namedtuple("SizeUnit", ["divider", "symbol", "name"])
CombinedUnit = namedtuple("CombinedUnit", ["decimal", "binary"])

# Decimal (base-10) multiples — the default for human-readable storage.
disk_size_units = (
    CombinedUnit(SizeUnit(1000**1, "KB", "kilobyte"), SizeUnit(1024**1, "KiB", "kibibyte")),
    CombinedUnit(SizeUnit(1000**2, "MB", "megabyte"), SizeUnit(1024**2, "MiB", "mebibyte")),
    CombinedUnit(SizeUnit(1000**3, "GB", "gigabyte"), SizeUnit(1024**3, "GiB", "gibibyte")),
    CombinedUnit(SizeUnit(1000**4, "TB", "terabyte"), SizeUnit(1024**4, "TiB", "tebibyte")),
    CombinedUnit(SizeUnit(1000**5, "PB", "petabyte"), SizeUnit(1024**5, "PiB", "pebibyte")),
)


class InvalidSize(Exception):
    """Raised when a string cannot be parsed into a byte size."""


def _tokenize(text):
    """
    Tokenize a string into numbers and text tokens.
    """
    tokens = []
    for token in re.split(r"(\d+(?:\.\d+)?)", text):
        token = token.strip()
        if re.match(r"\d+\.\d+", token):
            tokens.append(float(token))
        elif token.isdigit():
            tokens.append(int(token))
        elif token:
            tokens.append(token)
    return tokens


def parse_bytes(value):
    """
    Parse a human-readable byte size and return the number of bytes.

    Accepts strings like ``"10 TB"``, ``"500 GB"``, ``"42"``, and plain
    integers.  Returns ``None`` for empty/``None`` input.

    Raises :exc:`InvalidSize` when the input can't be parsed.
    """
    if value is None or value == "":
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)

    tokens = _tokenize(value)
    if not tokens:
        raise InvalidSize(f"Failed to parse byte size: {value!r}")

    if isinstance(tokens[0], (int, float)):
        normalized_unit = tokens[1].lower() if len(tokens) == 2 and isinstance(tokens[1], str) else ""
        if len(tokens) == 1 or normalized_unit.startswith("b"):
            return int(tokens[0])

        if normalized_unit:
            normalized_unit = normalized_unit.rstrip("s")
            for unit in disk_size_units:
                # Unambiguous binary units (KiB, MiB, GiB, etc.)
                if normalized_unit in (
                    unit.binary.symbol.lower(),
                    unit.binary.name.lower(),
                ):
                    return int(tokens[0] * unit.binary.divider)
                # Ambiguous decimal units (KB, MB, GB, etc.) — use decimal
                if normalized_unit in (
                    unit.decimal.symbol.lower(),
                    unit.decimal.name.lower(),
                ) or normalized_unit.startswith(unit.decimal.symbol[0].lower()):
                    return int(tokens[0] * unit.decimal.divider)

    raise InvalidSize(f"Failed to parse byte size: {value!r}")
