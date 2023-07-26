from django.contrib.auth.models import User
from django.contrib.admin.utils import NestedObjects
from django.db import DEFAULT_DB_ALIAS
from django.db import transaction

from coldfront.core.allocation.utils import has_cluster_access
from coldfront.core.user.models import EmailAddress as OldEmailAddress
from coldfront.core.user.utils_.merge_users.class_handlers import ClassHandlerFactory


class UserMergeRunner(object):
    """A class that merges two User objects into one.

    It identifies one User as a source and the other as a destination,
    merges the source's relationships, requests, etc. into the
    destination, and then deletes the source.

    It currently only supports merging when only one of the given Users
    has cluster access.
    """

    def __init__(self, user_1, user_2):
        """Identify which of the two Users should be merged into."""
        # src_user's data will be merged into dst_user.
        self._src_user = None
        self._dst_user = None
        self._identify_src_and_dst_users(user_1, user_2)

    @property
    def dst_user(self):
        return self._dst_user

    @property
    def src_user(self):
        return self._src_user

    @transaction.atomic
    def run(self):
        """Transfer dependencies from the source User to the destination
        User, then delete the source User."""
        try:
            with transaction.atomic():
                self._process_src_user_dependencies()
                self._src_user.delete()
                self._dst_user.refresh_from_db()
                self._display_dst_user_dependencies()
                raise Exception('Rolling back.')
        except Exception as e:
            # TODO
            print(e)

    @staticmethod
    def _classes_to_ignore():
        """Return a set of classes for which no processing should be
        done."""
        return {
            OldEmailAddress,
        }

    def _identify_src_and_dst_users(self, user_1, user_2):
        """Given two Users, determine which should be the source (the
        one having its data merged and then deleted) and which should be
        the destination (the one having data merged into it)."""
        user_1_has_cluster_access = has_cluster_access(user_1)
        user_2_has_cluster_access = has_cluster_access(user_2)
        if not (user_1_has_cluster_access or user_2_has_cluster_access):
            src, dst = user_2, user_1
        elif user_1_has_cluster_access and not user_2_has_cluster_access:
            src, dst = user_2, user_1
        elif not user_1_has_cluster_access and user_2_has_cluster_access:
            src, dst = user_1, user_2
        else:
            raise NotImplementedError(
                'Both Users have cluster access. This case is not currently '
                'handled.')
        self._src_user = src
        self._dst_user = dst

    def _process_src_user_dependencies(self):
        """Process each database object associated with the source User
        on a case-by-case basis."""
        collector = NestedObjects(using=DEFAULT_DB_ALIAS)
        collector.collect([self._src_user])
        objects = collector.nested()

        assert len(objects) == 2
        assert isinstance(objects[0], User)
        assert isinstance(objects[1], list)

        classes_to_ignore = self._classes_to_ignore()

        for obj in self._yield_nested_objects(objects[1]):

            if obj.__class__ in classes_to_ignore:
                continue

            class_handler_factory = ClassHandlerFactory()

            # Block other threads from retrieving this object until the end of
            # the transaction.
            obj = obj.__class__.objects.select_for_update().get(pk=obj.pk)

            try:
                handler = class_handler_factory.get_handler(
                    obj.__class__, self._src_user, self._dst_user, obj)
                handler.run()
            except ValueError:
                print(
                    f'Found no handler for object with class {obj.__class__}.')
            except Exception as e:
                # TODO
                print(e)

    def _display_dst_user_dependencies(self):
        """TODO"""
        collector = NestedObjects(using=DEFAULT_DB_ALIAS)
        collector.collect([self._dst_user])
        objects = collector.nested()

        for obj in self._yield_nested_objects(objects[1]):
            print(obj.__class__, obj, obj.__dict__)

    def _yield_nested_objects(self, objects):
        """Given a list that contains objects and lists of potentially-
        nested objects, return a generator that recursively yields
        objects."""
        for obj in objects:
            if isinstance(obj, list):
                yield from self._yield_nested_objects(obj)
            else:
                yield obj
