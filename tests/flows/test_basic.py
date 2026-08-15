# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django.test import TestCase

from coldfront.ras.flows import AllocationStatusFlow
from coldfront.ras.models import (
    Allocation,
)


class BasicFlowTest(TestCase):
    def test_flow_labels(self):
        """
        Test getting a transition label from a str
        """

        allocation = Allocation(justification="Test")
        flow = AllocationStatusFlow(allocation)
        self.assertEqual(flow.get_label("request"), "Request")
