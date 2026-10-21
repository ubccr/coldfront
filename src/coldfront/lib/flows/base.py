# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

import logging

from coldfront.core.notifications import send_system_notification

logger = logging.getLogger(__name__)


class ColdFrontFlow(object):
    """
    A base model for all ColdFront worklfow objects. Workflows define a set of
    states and transitions between them using a FSM field.

    - actions is a tuple that lists the valid ObjectActions for the Workflow
    """

    actions = tuple()

    # Registry mapping target_state -> list of callbacks
    # Callbacks are invoked when a transition successfully reaches the target state.
    # Callback signature: callback(obj, *, source=source, target=target)
    _target_callbacks: dict = {}

    # Registry mapping transition_slug -> list of permission callbacks
    # Callbacks are invoked before a transition to check if it should be allowed.
    # Callback signature: callback(obj, user) -> bool
    #   obj: the object being transitioned (e.g., Allocation instance)
    #   user: the User requesting the transition
    #   Returns True to allow the transition, False to deny.
    _transition_permission_callbacks: dict = {}

    def __init_subclass__(cls, **kwargs):
        """Ensure each subclass gets its own callback registries."""
        super().__init_subclass__(**kwargs)
        cls._target_callbacks = {}
        cls._transition_permission_callbacks = {}

    @classmethod
    def register_target_callback(cls, target_state, callback):
        """
        Register a callback to run when a transition reaches target_state.

        Args:
            target_state: The target state value (e.g., AllocationStatusChoices.STATUS_APPROVED)
            callback: A callable with signature callback(obj, *, source, target)
        """
        cls._target_callbacks.setdefault(target_state, []).append(callback)

    @classmethod
    def register_transition_permission_callback(cls, transition_slug, callback):
        """
        Register a permission callback for a specific transition.

        The callback receives (obj, user) and returns True to allow the
        transition or False to deny it.  If any registered callback returns
        False the transition is blocked.

        Args:
            transition_slug: The slug of the transition (e.g., "activate", "request")
            callback: A callable with signature callback(obj, user) -> bool
        """
        cls._transition_permission_callbacks.setdefault(transition_slug, []).append(callback)

    def _dispatch_target_callbacks(self, obj, source, target):
        """
        Call all registered callbacks for the given target state.

        Each callback is wrapped in a try-except so that a failure in one
        callback does not prevent other callbacks from running or, more
        importantly, does not break the core state transition.
        """
        for callback in self._target_callbacks.get(target, []):
            try:
                callback(obj, source=source, target=target)
            except Exception as e:
                logger.exception(
                    "Error in callback %r for target state %r",
                    callback.__name__ if hasattr(callback, "__name__") else callback,
                    target,
                )

                # Notify admins about the callback failure
                cb_name = callback.__name__ if hasattr(callback, "__name__") else repr(callback)
                url = getattr(obj, "get_absolute_url", lambda: None)()
                send_system_notification(
                    target=obj,
                    subject=f"Callback failed: {cb_name}",
                    text=(
                        f"A transition callback '{cb_name}' for target state "
                        f"'{target}' failed on {type(obj).__name__} {obj}.\n\n"
                        f"Error: {e}"
                    ),
                    url=url,
                )

    def _check_permission_callbacks(self, transition_slug, obj, user):
        """
        Run all registered permission callbacks for a given transition slug.

        Returns True if all callbacks return True, False if any callback
        returns False.
        """
        for callback in self._transition_permission_callbacks.get(transition_slug, []):
            if not callback(obj, user):
                return False
        return True

    @classmethod
    def get_actions(cls, transitions):
        """
        Return the ObjectActions for the given transitions
        """
        actions = []
        for t in transitions:
            for a in cls.actions:
                if t == a.transition:
                    actions.append(a)

        return actions

    def get_label(self, transition):
        """
        Return the label for the given transition
        """
        if func := getattr(self, transition, None):
            return func.label

        return ""


def register_target_callback(flow_cls, target_state):
    """
    Decorator factory: register a callback function with a flow class for a
    given target state.

    The decorated function receives (obj, *, source, target) and is called
    after a transition successfully reaches target_state.

    Usage:
        @register_target_callback(AllocationStatusFlow, AllocationStatusChoices.STATUS_REQUESTED)
        def on_allocation_requested(allocation, *, source, target):
            ...

    This is equivalent to:
        AllocationStatusFlow.register_target_callback(
            AllocationStatusChoices.STATUS_REQUESTED,
            on_allocation_requested,
        )
    """

    def decorator(func):
        flow_cls.register_target_callback(target_state, func)
        return func

    return decorator


def register_transition_permission_callback(flow_cls, transition_slug):
    """
    Decorator factory: register a permission callback function with a flow
    class for a given transition slug.

    The callback receives (obj, user) and returns True to allow the
    transition or False to deny it.  If any registered callback returns
    False, the transition is blocked.

    Usage:
        @register_transition_permission_callback(
            AllocationStatusFlow, "activate"
        )
        def on_activate_check(allocation, user):
            ...
    """

    def decorator(func):
        flow_cls.register_transition_permission_callback(transition_slug, func)
        return func

    return decorator
