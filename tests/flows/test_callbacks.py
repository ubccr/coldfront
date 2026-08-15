# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from unittest.mock import Mock

from django.contrib.contenttypes.models import ContentType
from django.test import TestCase

from coldfront.ras.choices import AllocationStatusChoices
from coldfront.ras.flows import AllocationStatusFlow
from coldfront.ras.models import (
    Allocation,
    Project,
    Resource,
    ResourceType,
)
from coldfront.users.models import User


class ErrorCallback:
    """A callable that raises RuntimeError on call, for testing error handling."""

    def __init__(self):
        self.call_count = 0

    def __call__(self, obj, *, source, target):
        self.call_count += 1
        raise RuntimeError("callback failed intentionally")

    def __name__(self):
        return "ErrorCallback"


class TargetCallbackTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        user = User.objects.create(username="User1")
        project = Project.objects.create(name="Project 1", owner=user)
        resource_type = ResourceType.objects.create(name="Cluster")
        resource = Resource.objects.create(name="Resource 1", slug="r-1", resource_type=resource_type)
        resource_ct = ContentType.objects.get_for_model(Resource)
        Allocation.objects.create(
            justification="Need resources",
            project=project,
            owner=user,
            resource_object_type=resource_ct,
            resource_object_id=resource.pk,
        )

    def setUp(self):
        # Clear any registered callbacks before each test
        AllocationStatusFlow._target_callbacks = {}

    def test_registered_callback_invoked_on_approve(self):
        """A callback registered for STATUS_APPROVED should be called when approve() succeeds."""
        callback = Mock()
        AllocationStatusFlow.register_target_callback(AllocationStatusChoices.STATUS_APPROVED, callback)

        allocation = Allocation.objects.first()
        flow = AllocationStatusFlow(allocation)

        flow.request()
        flow.approve()

        callback.assert_called_once()
        args, kwargs = callback.call_args
        self.assertEqual(args[0], allocation)
        self.assertEqual(kwargs["source"], AllocationStatusChoices.STATUS_REQUESTED)
        self.assertEqual(kwargs["target"], AllocationStatusChoices.STATUS_APPROVED)

    def test_registered_callback_invoked_on_expire(self):
        """A callback registered for STATUS_EXPIRED should be called when expire() succeeds."""
        callback = Mock()
        AllocationStatusFlow.register_target_callback(AllocationStatusChoices.STATUS_EXPIRED, callback)

        allocation = Allocation.objects.first()
        flow = AllocationStatusFlow(allocation)

        flow.request()
        flow.approve()
        flow.activate()
        flow.expire()

        callback.assert_called_once()
        args, kwargs = callback.call_args
        self.assertEqual(args[0], allocation)
        self.assertEqual(kwargs["source"], AllocationStatusChoices.STATUS_ACTIVE)
        self.assertEqual(kwargs["target"], AllocationStatusChoices.STATUS_EXPIRED)

    def test_registered_callback_invoked_on_deny(self):
        """A callback registered for STATUS_DENIED should be called when deny() succeeds."""
        callback = Mock()
        AllocationStatusFlow.register_target_callback(AllocationStatusChoices.STATUS_DENIED, callback)

        allocation = Allocation.objects.first()
        flow = AllocationStatusFlow(allocation)

        flow.request()
        flow.deny()

        callback.assert_called_once()
        args, kwargs = callback.call_args
        self.assertEqual(args[0], allocation)
        self.assertEqual(kwargs["source"], AllocationStatusChoices.STATUS_REQUESTED)
        self.assertEqual(kwargs["target"], AllocationStatusChoices.STATUS_DENIED)

    def test_registered_callback_invoked_on_revoke(self):
        """A callback registered for STATUS_REVOKED should be called when revoke() succeeds."""
        callback = Mock()
        AllocationStatusFlow.register_target_callback(AllocationStatusChoices.STATUS_REVOKED, callback)

        allocation = Allocation.objects.first()
        flow = AllocationStatusFlow(allocation)

        flow.request()
        flow.approve()
        flow.activate()
        flow.revoke()

        callback.assert_called_once()
        args, kwargs = callback.call_args
        self.assertEqual(args[0], allocation)
        self.assertEqual(kwargs["source"], AllocationStatusChoices.STATUS_ACTIVE)
        self.assertEqual(kwargs["target"], AllocationStatusChoices.STATUS_REVOKED)

    def test_registered_callback_invoked_on_renew(self):
        """A callback registered for STATUS_RENEW should be called when renew() succeeds."""
        callback = Mock()
        AllocationStatusFlow.register_target_callback(AllocationStatusChoices.STATUS_RENEW, callback)

        allocation = Allocation.objects.first()
        flow = AllocationStatusFlow(allocation)

        flow.request()
        flow.approve()
        flow.activate()
        flow.expire()
        flow.renew()

        callback.assert_called_once()
        args, kwargs = callback.call_args
        self.assertEqual(args[0], allocation)
        self.assertEqual(kwargs["source"], AllocationStatusChoices.STATUS_EXPIRED)
        self.assertEqual(kwargs["target"], AllocationStatusChoices.STATUS_RENEW)

    def test_multiple_callbacks_for_same_target(self):
        """Multiple callbacks registered for the same target should all be called."""
        callback_a = Mock()
        callback_b = Mock()
        AllocationStatusFlow.register_target_callback(AllocationStatusChoices.STATUS_APPROVED, callback_a)
        AllocationStatusFlow.register_target_callback(AllocationStatusChoices.STATUS_APPROVED, callback_b)

        allocation = Allocation.objects.first()
        flow = AllocationStatusFlow(allocation)

        flow.request()
        flow.approve()

        callback_a.assert_called_once()
        callback_b.assert_called_once()

    def test_callback_not_invoked_for_unregistered_target(self):
        """A callback registered for one target should NOT be called for another target."""
        callback = Mock()
        AllocationStatusFlow.register_target_callback(AllocationStatusChoices.STATUS_EXPIRED, callback)

        allocation = Allocation.objects.first()
        flow = AllocationStatusFlow(allocation)

        flow.request()
        flow.approve()
        flow.activate()

        # Callback was for EXPIRED, not ACTIVE — should not have been called
        callback.assert_not_called()

    def test_no_callbacks_registered_does_not_raise(self):
        """When no callbacks are registered, transitions should still succeed."""
        allocation = Allocation.objects.first()
        flow = AllocationStatusFlow(allocation)

        flow.request()
        flow.approve()
        flow.activate()

        self.assertEqual(allocation.status, AllocationStatusChoices.STATUS_ACTIVE)

    def test_register_target_callback_is_classmethod(self):
        """register_target_callback should work on the class, not just instances."""
        callback = Mock()
        AllocationStatusFlow.register_target_callback(AllocationStatusChoices.STATUS_APPROVED, callback)

        allocation = Allocation.objects.first()
        flow = AllocationStatusFlow(allocation)

        flow.request()
        flow.approve()

        callback.assert_called_once()

    def test_callback_receives_source_and_target_as_kwargs(self):
        """Callback should receive source and target as keyword arguments."""
        callback = Mock()
        AllocationStatusFlow.register_target_callback(AllocationStatusChoices.STATUS_APPROVED, callback)

        allocation = Allocation.objects.first()
        flow = AllocationStatusFlow(allocation)

        flow.request()
        flow.approve()

        kwargs = callback.call_args[1]
        self.assertIn("source", kwargs)
        self.assertIn("target", kwargs)

    def test_callback_receives_object_as_first_arg(self):
        """Callback should receive the object (allocation) as the first positional argument."""
        callback = Mock()
        AllocationStatusFlow.register_target_callback(AllocationStatusChoices.STATUS_APPROVED, callback)

        allocation = Allocation.objects.first()
        flow = AllocationStatusFlow(allocation)

        flow.request()
        flow.approve()

        args = callback.call_args[0]
        self.assertEqual(args[0], allocation)

    def test_callback_error_does_not_break_transition(self):
        """If a callback raises, the transition should still succeed."""
        error_cb = ErrorCallback()
        AllocationStatusFlow.register_target_callback(AllocationStatusChoices.STATUS_APPROVED, error_cb)

        allocation = Allocation.objects.first()
        flow = AllocationStatusFlow(allocation)

        flow.request()
        # Should not raise despite the error callback
        flow.approve()

        self.assertEqual(allocation.status, AllocationStatusChoices.STATUS_APPROVED)
        self.assertEqual(error_cb.call_count, 1)

    def test_callback_error_does_not_prevent_other_callbacks(self):
        """If one callback raises, other callbacks for the same target should still run."""
        error_cb = ErrorCallback()
        good_callback = Mock()
        AllocationStatusFlow.register_target_callback(AllocationStatusChoices.STATUS_APPROVED, error_cb)
        AllocationStatusFlow.register_target_callback(AllocationStatusChoices.STATUS_APPROVED, good_callback)

        allocation = Allocation.objects.first()
        flow = AllocationStatusFlow(allocation)

        flow.request()
        flow.approve()

        self.assertEqual(error_cb.call_count, 1)
        good_callback.assert_called_once()
