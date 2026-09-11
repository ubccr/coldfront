# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

"""Tests for ``coldfront.slurm.parser`` SlurmTime parsing/formatting.

Covers every slurm.conf time format from the man page (minutes,
minutes:seconds, hours:minutes:seconds, days-hours, days-hours:minutes,
days-hours:minutes:seconds, UNLIMITED) plus the INFINITE synonym.
"""

from datetime import timedelta

from django.test import SimpleTestCase

from coldfront.slurm.parser import SlurmTime, format_slurm_time, parse_slurm_time


class ParseSlurmTimeTestCase(SimpleTestCase):
    def test_minutes(self):
        self.assertEqual(parse_slurm_time("10").duration, timedelta(minutes=10))

    def test_minutes_seconds(self):
        self.assertEqual(parse_slurm_time("10:30").duration, timedelta(minutes=10, seconds=30))

    def test_hours_minutes_seconds(self):
        self.assertEqual(parse_slurm_time("72:00:00").duration, timedelta(hours=72))

    def test_days_hours(self):
        self.assertEqual(parse_slurm_time("30-0").duration, timedelta(days=30))

    def test_days_hours_minutes(self):
        self.assertEqual(parse_slurm_time("30-12:00").duration, timedelta(days=30, hours=12))

    def test_days_hours_minutes_seconds(self):
        self.assertEqual(parse_slurm_time("30-12:00:00").duration, timedelta(days=30, hours=12))

    def test_unlimited(self):
        self.assertTrue(parse_slurm_time("UNLIMITED").is_unlimited())

    def test_infinite_is_unlimited_synonym(self):
        self.assertTrue(parse_slurm_time("INFINITE").is_unlimited())

    def test_empty_is_zero(self):
        self.assertEqual(parse_slurm_time("").duration, timedelta(0))

    def test_invalid_raises_value_error(self):
        with self.assertRaises(ValueError):
            parse_slurm_time("bogus")


class FormatSlurmTimeTestCase(SimpleTestCase):
    def test_unlimited(self):
        self.assertEqual(format_slurm_time(SlurmTime()), "UNLIMITED")

    def test_sub_day(self):
        self.assertEqual(format_slurm_time(SlurmTime(duration=timedelta(minutes=10))), "00:10:00")

    def test_multi_hour(self):
        self.assertEqual(format_slurm_time(SlurmTime(duration=timedelta(hours=12))), "12:00:00")

    def test_whole_days_renders_days_format(self):
        # 72h == 3 days; Slurm's canonical display uses the D-HH:MM:SS form.
        self.assertEqual(format_slurm_time(SlurmTime(duration=timedelta(hours=72))), "3-00:00:00")

    def test_days(self):
        self.assertEqual(
            format_slurm_time(SlurmTime(duration=timedelta(days=30, hours=12))),
            "30-12:00:00",
        )

    def test_helpers(self):
        self.assertIsNone(SlurmTime().to_minutes())
        self.assertIsNone(SlurmTime().to_seconds())
        self.assertEqual(SlurmTime(duration=timedelta(hours=1)).to_minutes(), 60)
        self.assertEqual(SlurmTime(duration=timedelta(hours=24)).to_seconds(), 86400)
