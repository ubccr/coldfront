# SPDX-FileCopyrightText: (C) ColdFront Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging

from django.test import TestCase, override_settings

from coldfront.core.utils.common import import_from_settings

logging.disable(logging.CRITICAL)


class PortalViewBaseTest(TestCase):
    """Base class for portal view tests."""

    @classmethod
    def setUpTestData(cls):
        """Test Data setup for all portal view tests."""
        pass


class CenterSummaryViewTest(PortalViewBaseTest):
    """Tests for center summary view"""

    @classmethod
    def setUpTestData(cls):
        """Set up users and project for testing"""
        cls.url = "/center-summary"
        super(PortalViewBaseTest, cls).setUpTestData()

    def test_centersummary_renders_field_of_science_not_hidden(self):
        self.assertFalse(import_from_settings("FIELD_OF_SCIENCE_HIDE", True))
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "<!-- Start Allocation by Field of Science -->")
        # sanity check for other chart
        self.assertContains(response, "<!-- Start Allocation Charts -->")

    @override_settings(FIELD_OF_SCIENCE_HIDE=True)
    def test_centersummary_renders_field_of_science_hidden(self):
        self.assertTrue(import_from_settings("FIELD_OF_SCIENCE_HIDE", False))
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "<!-- Start Allocation by Field of Science -->")
        # sanity check for other chart
        self.assertContains(response, "<!-- Start Allocation Charts -->")
