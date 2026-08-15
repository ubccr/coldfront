# SPDX-FileCopyrightText: (C) DigitalOcean, LLC
# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django.core.exceptions import ObjectDoesNotExist
from django.db import router, transaction
from django.http import Http404
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from coldfront.api.serializers.features import BulkOperationSerializer
from coldfront.core.models import ObjectType

__all__ = (
    "CustomFieldsMixin",
    "ObjectValidationMixin",
    "SequentialBulkCreatesMixin",
    "WorkflowViewSetMixin",
)


class CustomFieldsMixin:
    """
    For models which support custom fields, populate the `custom_fields` context.
    """

    def get_serializer_context(self):
        context = super().get_serializer_context()

        if hasattr(self.queryset.model, "custom_fields"):
            object_type = ObjectType.objects.get_for_model(self.queryset.model)
            context.update(
                {
                    "custom_fields": object_type.custom_fields.all(),
                }
            )

        return context


class SequentialBulkCreatesMixin:
    """
    Perform bulk creation of new objects sequentially, rather than all at once. This ensures that any validation
    which depends on the evaluation of existing objects functions appropriately.
    """

    def create(self, request, *args, **kwargs):
        with transaction.atomic(using=router.db_for_write(self.queryset.model)):
            if not isinstance(request.data, list):
                # Creating a single object
                return super().create(request, *args, **kwargs)

            return_data = []
            for data in request.data:
                serializer = self.get_serializer(data=data)
                serializer.is_valid(raise_exception=True)
                self.perform_create(serializer)
                return_data.append(serializer.data)

            headers = self.get_success_headers(serializer.data)

            return Response(return_data, status=status.HTTP_201_CREATED, headers=headers)


class ObjectValidationMixin:
    def _validate_objects(self, instance):
        """
        Check that the provided instance or list of instances are matched by the current queryset. This confirms that
        any newly created or modified objects abide by the attributes granted by any applicable ObjectPermissions.
        """
        if type(instance) is list:
            # Check that all instances are still included in the view's queryset
            conforming_count = self.queryset.filter(pk__in=[obj.pk for obj in instance]).count()
            if conforming_count != len(instance):
                raise ObjectDoesNotExist
        elif not self.queryset.filter(pk=instance.pk).exists():
            raise ObjectDoesNotExist


class BulkUpdateModelMixin:
    """
    Support bulk modification of objects using the list endpoint for a model. Accepts a PATCH action with a list of one
    or more JSON objects, each specifying the numeric ID of an object to be updated as well as the attributes to be set.
    For example:

    PATCH /api/ras/projects/
    [
        {
            "id": 123,
            "name": "New name"
        },
        {
            "id": 456,
            "status": "planned"
        }
    ]
    """

    def get_bulk_update_queryset(self):
        return self.get_queryset()

    def bulk_update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        serializer = BulkOperationSerializer(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)
        qs = self.get_bulk_update_queryset().filter(pk__in=[o["id"] for o in serializer.data])

        # Map update data by object ID
        update_data = {obj.pop("id"): obj for obj in request.data}

        object_pks = self.perform_bulk_update(qs, update_data, partial=partial)

        # Prefetch related objects for all updated instances
        qs = self.get_queryset().filter(pk__in=object_pks)
        serializer = self.get_serializer(qs, many=True)

        return Response(serializer.data, status=status.HTTP_200_OK)

    def perform_bulk_update(self, objects, update_data, partial):
        updated_pks = []
        with transaction.atomic(using=router.db_for_write(self.queryset.model)):
            for obj in objects:
                data = update_data.get(obj.id)
                if hasattr(obj, "snapshot"):
                    obj.snapshot()
                serializer = self.get_serializer(obj, data=data, partial=partial)
                serializer.is_valid(raise_exception=True)
                self.perform_update(serializer)
                updated_pks.append(obj.pk)

        return updated_pks

    def bulk_partial_update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return self.bulk_update(request, *args, **kwargs)


class BulkDestroyModelMixin:
    """
    Support bulk deletion of objects using the list endpoint for a model. Accepts a DELETE action with a list of one
    or more JSON objects, each specifying the numeric ID of an object to be deleted. For example:

    DELETE /api/ras/projects/
    [
        {"id": 123},
        {"id": 456}
    ]
    """

    def get_bulk_destroy_queryset(self):
        return self.get_queryset()

    def bulk_destroy(self, request, *args, **kwargs):
        serializer = BulkOperationSerializer(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)
        qs = self.get_bulk_destroy_queryset().filter(pk__in=[o["id"] for o in serializer.validated_data])

        # Compile any changelog messages to be recorded on the objects being deleted
        changelog_messages = {o["id"]: o.get("changelog_message") for o in serializer.validated_data}

        self.perform_bulk_destroy(qs, changelog_messages)

        return Response(status=status.HTTP_204_NO_CONTENT)

    def perform_bulk_destroy(self, objects, changelog_messages=None):
        changelog_messages = changelog_messages or {}
        with transaction.atomic(using=router.db_for_write(self.queryset.model)):
            for obj in objects:
                if hasattr(obj, "snapshot"):
                    obj.snapshot()
                obj._changelog_message = changelog_messages.get(obj.pk)
                self.perform_destroy(obj)


class WorkflowViewSetMixin:
    """
    Mixin for ViewSets that manage workflow-enabled models.

    Adds ``@action`` endpoints for each transition defined in ``flow_class.actions``.
    Each endpoint accepts POST and runs the transition, returning the updated object.

    Usage::

        class AllocationViewSet(WorkflowViewSetMixin, ColdFrontModelViewSet):
            queryset = Allocation.objects.all()
            serializer_class = AllocationSerializer
            flow_class = AllocationStatusFlow

    The mixin automatically registers POST /{pk}/{transition_name}/ for each
    transition (e.g., approve, deny, activate).
    """

    flow_class = None
    # Override to specify a custom permission check per transition
    _transition_permissions = {}

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if cls.flow_class is not None:
            cls._register_flow_actions()

    @classmethod
    def _register_flow_actions(cls):
        """Dynamically create @action endpoints for each transition in flow_class.actions."""
        for action_obj in cls.flow_class.actions:
            name = action_obj.name
            if hasattr(cls, name):
                continue  # don't override an existing method

            # Bind name as a default arg to avoid closure mutation issues
            def make_handler(transition_name):
                @action(detail=True, methods=["post"], url_path=transition_name, url_name=transition_name)
                def handler(self, request, *args, **kwargs):
                    return self._execute_transition(request, transition_name)

                handler.__name__ = transition_name
                handler.__qualname__ = f"{cls.__name__}.{transition_name}"
                handler.__module__ = cls.__module__
                return handler

            setattr(cls, name, make_handler(name))

    def _execute_transition(self, request, transition_name):
        """
        Execute a workflow transition via the API.

        Loads the object, instantiates the flow, validates the transition
        (FSM + permissions), runs it inside a transaction, and returns the
        updated object.
        """
        # Resolve the object (standard DRF lookup)
        pk = request.resolver_match.kwargs.get("pk")
        if pk is None:
            raise Http404
        obj = self.get_object()

        # Instantiate the flow
        flow = self.flow_class(obj)

        # Get the transition function
        transition_func = getattr(flow, transition_name, None)
        if transition_func is None:
            return Response(
                {"error": f"Transition '{transition_name}' is not defined"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Gate 1: FSM validation — can the transition proceed?
        if not transition_func.can_proceed():
            return Response(
                {"error": f"Cannot {transition_name} allocation in current status"},
                status=status.HTTP_409_CONFLICT,
            )

        # Gate 2: FSM permission callbacks
        if not transition_func.has_perm(request.user):
            return Response(
                {"error": f"You do not have permission to {transition_name} this allocation"},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Run the transition inside a transaction
        with transaction.atomic(using=router.db_for_write(self.queryset.model)):
            transition_func()
            obj.refresh_from_db()

        # Return the updated object
        serializer = self.get_serializer(obj)
        return Response(serializer.data, status=status.HTTP_200_OK)
