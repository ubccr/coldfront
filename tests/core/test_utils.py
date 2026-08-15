# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django.test import TestCase

from coldfront.utils.bytes import InvalidSize, parse_bytes


class ParseBytesTest(TestCase):
    def test_parse_plain_number_string(self):
        self.assertEqual(parse_bytes("42"), 42)

    def test_parse_plain_int(self):
        self.assertEqual(parse_bytes(42), 42)

    def test_parse_plain_float(self):
        self.assertEqual(parse_bytes(42.5), 42)

    def test_parse_kb(self):
        self.assertEqual(parse_bytes("1 KB"), 1000)

    def test_parse_mb(self):
        self.assertEqual(parse_bytes("1 MB"), 1_000_000)

    def test_parse_gb(self):
        self.assertEqual(parse_bytes("1 GB"), 1_000_000_000)

    def test_parse_tb(self):
        self.assertEqual(parse_bytes("10 TB"), 10_000_000_000_000)

    def test_parse_pb(self):
        self.assertEqual(parse_bytes("1 PB"), 1_000_000_000_000_000)

    def test_parse_kib(self):
        self.assertEqual(parse_bytes("1 KiB"), 1024)

    def test_parse_mib(self):
        self.assertEqual(parse_bytes("1 MiB"), 1_048_576)

    def test_parse_gib(self):
        self.assertEqual(parse_bytes("1 GiB"), 1_073_741_824)

    def test_parse_tib(self):
        self.assertEqual(parse_bytes("1 TiB"), 1_099_511_627_776)

    def test_parse_pib(self):
        self.assertEqual(parse_bytes("1 PiB"), 1_125_899_906_842_624)

    def test_parse_with_spaces(self):
        self.assertEqual(parse_bytes("10  TB"), 10_000_000_000_000)

    def test_parse_decimal(self):
        self.assertEqual(parse_bytes("1.5 GB"), 1_500_000_000)

    def test_parse_without_space(self):
        self.assertEqual(parse_bytes("10TB"), 10_000_000_000_000)

    def test_parse_bytes_unit(self):
        self.assertEqual(parse_bytes("5 bytes"), 5)

    def test_parse_byte_unit(self):
        self.assertEqual(parse_bytes("5 byte"), 5)

    def test_parse_empty_string(self):
        self.assertIsNone(parse_bytes(""))

    def test_parse_none(self):
        self.assertIsNone(parse_bytes(None))

    def test_parse_invalid_string(self):
        with self.assertRaises(InvalidSize):
            parse_bytes("not a size")

    def test_parse_garbage(self):
        with self.assertRaises(InvalidSize):
            parse_bytes("5 Z")

    def test_parse_ambiguous_decimal(self):
        """Ambiguous prefixes (K, M, G) should default to decimal."""
        self.assertEqual(parse_bytes("1 K"), 1000)
        self.assertEqual(parse_bytes("1 M"), 1_000_000)
        self.assertEqual(parse_bytes("1 G"), 1_000_000_000)

    def test_parse_plural(self):
        self.assertEqual(parse_bytes("5 kilobytes"), 5000)
        self.assertEqual(parse_bytes("5 megabytes"), 5_000_000)
