# SPDX-FileCopyrightText: (C) ColdFront Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging

from django.test import TestCase

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

    def test_centersummary_renders(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Active Allocations and Users")
        self.assertContains(response, "Resources and Allocations Summary")
        self.assertNotContains(response, "We're having a bit of system trouble at the moment. Please check back soon!")
