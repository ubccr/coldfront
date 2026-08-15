# SPDX-FileCopyrightText: (C) DigitalOcean, LLC
# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import CASCADE, RESTRICT
from django.db.models.fields.reverse_related import ManyToManyRel, ManyToOneRel
from django.db.models.signals import m2m_changed, post_migrate, post_save, pre_delete
from django.dispatch import Signal, receiver

from coldfront.context import current_request, signals_received
from coldfront.core.choices import ObjectChangeActionChoices
from coldfront.core.events import OBJECT_CREATED, OBJECT_DELETED, OBJECT_UPDATED
from coldfront.core.models import CustomField, ObjectChange, ObjectType, Tag
from coldfront.models.features import ChangeLoggingMixin

# Job lifecycle signals
job_start = Signal()
job_end = Signal()


@receiver(post_migrate)
def update_object_types(sender, **kwargs):
    """
    Create or update the corresponding ObjectType for each model within the migrated app.
    """
    for model in sender.get_models():
        app_label, model_name = model._meta.label_lower.split(".")

        # Determine whether model is public and its supported features
        is_public = ObjectType.model_is_public(model)
        features = ObjectType.get_model_features_dict(model)

        # Create/update the ObjectType for the model
        try:
            ot = ObjectType.objects.get_by_natural_key(app_label=app_label, model=model_name)
            ot.public = is_public
            ot.features = features
            ot.save()
        except ObjectDoesNotExist:
            ObjectType.objects.create(
                app_label=app_label,
                model=model_name,
                public=is_public,
                features=features,
            )


@receiver((post_save, m2m_changed))
def handle_changed_object(sender, instance, **kwargs):
    """
    Fires when an object is created or updated.
    """
    m2m_changed = False

    if not hasattr(instance, "to_objectchange"):
        return

    # Get the current request, or bail if not set
    request = current_request.get()
    if request is None:
        return

    # Determine the type of change being made
    if kwargs.get("created"):
        event_type = OBJECT_CREATED
    elif "created" in kwargs:
        event_type = OBJECT_UPDATED
    elif kwargs.get("action") in ["post_add", "post_remove"] and kwargs["pk_set"]:
        # m2m_changed with objects added or removed
        m2m_changed = True
        event_type = OBJECT_UPDATED
    elif kwargs.get("action") == "post_clear":
        # Handle clearing of an M2M field
        if kwargs.get("model") == Tag and getattr(instance, "_prechange_snapshot", {}).get("tags"):
            # Handle generation of M2M changes for Tags which have a previous value (ignoring changes where the
            # prechange snapshot is empty)
            m2m_changed = True
            event_type = OBJECT_UPDATED
        else:
            # Other endpoints are unimpacted as they send post_add and post_remove
            # This will impact changes that utilize clear() however so we may want to give consideration for this branch
            return
    else:
        return

    # Create/update an ObjectChange record for this change
    action = {
        OBJECT_CREATED: ObjectChangeActionChoices.ACTION_CREATE,
        OBJECT_UPDATED: ObjectChangeActionChoices.ACTION_UPDATE,
        OBJECT_DELETED: ObjectChangeActionChoices.ACTION_DELETE,
    }[event_type]
    objectchange = instance.to_objectchange(action)
    # If this is a many-to-many field change, check for a previous ObjectChange instance recorded
    # for this object by this request and update it
    if m2m_changed and (
        prev_change := ObjectChange.objects.filter(
            changed_object_type=ContentType.objects.get_for_model(instance),
            changed_object_id=instance.pk,
            request_id=request.id,
        ).first()
    ):
        prev_change.postchange_data = objectchange.postchange_data
        prev_change.save()
    elif objectchange and objectchange.has_changes:
        objectchange.user = request.user
        objectchange.request_id = request.id
        objectchange.save()

    # Ensure that we're working with fresh M2M assignments
    if m2m_changed:
        instance.refresh_from_db()


@receiver(pre_delete)
def handle_deleted_object(sender, instance, **kwargs):
    """
    Fires when an object is deleted.
    """
    # Get the current request, or bail if not set
    request = current_request.get()
    if request is None:
        return

    _signals_received = signals_received.get()

    # Check whether we've already processed a pre_delete signal for this object. (This can
    # happen e.g. when both a parent object and its child are deleted simultaneously, due
    # to cascading deletion.)
    if "pre_delete" not in _signals_received:
        _signals_received["pre_delete"] = set()
    signature = (ContentType.objects.get_for_model(instance), instance.pk)
    if signature in _signals_received["pre_delete"]:
        return
    _signals_received["pre_delete"].add(signature)

    # Record an ObjectChange if applicable
    if hasattr(instance, "to_objectchange"):
        if hasattr(instance, "snapshot") and not getattr(instance, "_prechange_snapshot", None):
            instance.snapshot()
        objectchange = instance.to_objectchange(ObjectChangeActionChoices.ACTION_DELETE)
        objectchange.user = request.user
        objectchange.request_id = request.id
        objectchange.save()

    # Django does not automatically send an m2m_changed signal for the reverse direction of a
    # many-to-many relationship (see https://code.djangoproject.com/ticket/17688), so we need to
    # trigger one manually. We do this by checking for any reverse M2M relationships on the
    # instance being deleted, and explicitly call .remove() on the remote M2M field to delete
    # the association. This triggers an m2m_changed signal with the `post_remove` action type
    # for the forward direction of the relationship, ensuring that the change is recorded.
    # Similarly, for many-to-one relationships, we set the value on the related object to None
    # and save it to trigger a change record on that object.
    #
    # Skip this for private models (e.g. CablePath) whose lifecycle is an internal
    # implementation detail. Django's on_delete handlers (e.g. SET_NULL) already take
    # care of the database integrity; recording changelog entries for the related
    # objects would be spurious. (Ref: #21390)
    if not getattr(instance, "_coldfront_private", False):
        for relation in instance._meta.related_objects:
            if type(relation) not in [ManyToManyRel, ManyToOneRel]:
                continue
            related_model = relation.related_model
            related_field_name = relation.remote_field.name
            if not issubclass(related_model, ChangeLoggingMixin):
                # We only care about triggering the m2m_changed signal for models which support
                # change logging
                continue
            for obj in related_model.objects.filter(**{related_field_name: instance.pk}):
                obj.snapshot()  # Ensure the change record includes the "before" state
                if type(relation) is ManyToManyRel:
                    getattr(obj, related_field_name).remove(instance)
                elif type(relation) is ManyToOneRel and relation.null and relation.on_delete not in (CASCADE, RESTRICT):
                    setattr(obj, related_field_name, None)
                    obj.save()


def handle_cf_added_obj_types(instance, action, pk_set, **kwargs):
    """
    Handle the population of default/null values when a CustomField is added to one or more ContentTypes.
    """
    if action == "post_add":
        instance.populate_initial_data(ContentType.objects.filter(pk__in=pk_set))


def handle_cf_removed_obj_types(instance, action, pk_set, **kwargs):
    """
    Handle the cleanup of old custom field data when a CustomField is removed from one or more ContentTypes.
    """
    if action == "post_remove":
        instance.remove_stale_data(ContentType.objects.filter(pk__in=pk_set))


def handle_cf_renamed(instance, created, **kwargs):
    """
    Handle the renaming of custom field data on objects when a CustomField is renamed.
    """
    if not created and instance.name != instance._name:
        instance.rename_object_data(old_name=instance._name, new_name=instance.name)


def handle_cf_deleted(instance, **kwargs):
    """
    Handle the cleanup of old custom field data when a CustomField is deleted.
    """
    instance.remove_stale_data(instance.object_types.all())


post_save.connect(handle_cf_renamed, sender=CustomField)
pre_delete.connect(handle_cf_deleted, sender=CustomField)
m2m_changed.connect(handle_cf_added_obj_types, sender=CustomField.object_types.through)
m2m_changed.connect(handle_cf_removed_obj_types, sender=CustomField.object_types.through)
