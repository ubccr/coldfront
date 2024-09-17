from django.test import TestCase
from coldfront.core.allocation.models import AllocationStatusChoice
from coldfront.plugins.qumulo.management.commands.add_allocation_status import (
    Command,
)


class TestQumuloPluginSetup(TestCase):
    def setUp(self):
        cmd = Command()
        cmd.handle()

    def test_pending_status_exists(self):
        gotObject = None
        existsCallIsSafe = True
        try:
            gotObject = AllocationStatusChoice.objects.get(name="Pending")
        except Exception:
            existsCallIsSafe = False
        self.assertTrue(existsCallIsSafe)
        if existsCallIsSafe is True:
            self.assertNotEqual(gotObject, None)
