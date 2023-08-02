from django.contrib.auth.models import User
from django.contrib.admin.utils import NestedObjects
from django.db import DEFAULT_DB_ALIAS
from django.db import transaction

from coldfront.core.allocation.utils import has_cluster_access
from coldfront.core.user.models import EmailAddress as OldEmailAddress
from coldfront.core.user.utils_.merge_users.class_handlers import ClassHandlerFactory


class UserMergeError(Exception):
    pass


class UserMergeRollback(Exception):
    pass


class UserMergeRunner(object):
    """A class that merges two User objects into one.

    It identifies one User as a source and the other as a destination,
    merges the source's relationships, requests, etc. into the
    destination, and then deletes the source.

    It currently only supports merging when only one of the given Users
    has cluster access.
    """

    def __init__(self, user_1, user_2, reporting_strategies=None):
        """Identify which of the two Users should be merged into."""
        self._dry = False
        # src_user's data will be merged into dst_user.
        self._src_user = None
        self._dst_user = None
        self._src_user_pk = None
        self._identify_src_and_dst_users(user_1, user_2)

        # Report messages using each of the given strategies.
        self._reporting_strategies = []
        if isinstance(reporting_strategies, list):
            for strategy in reporting_strategies:
                self._reporting_strategies.append(strategy)

    @property
    def dst_user(self):
        return self._dst_user

    @property
    def src_user(self):
        return self._src_user

    def dry_run(self):
        """Attempt to run the merge, but rollback before committing
        changes."""
        self._dry = True
        self.run()

    @transaction.atomic
    def run(self):
        """Transfer dependencies from the source User to the destination
        User, then delete the source User."""
        try:
            with transaction.atomic():
                self._select_users_for_update()
                self._process_src_user_dependencies()
                self._src_user.delete()
                if self._dry:
                    self._rollback()
        except UserMergeRollback:
            # The dry run succeeded, and the transaction was rolled back.
            self._reset_users()
        except Exception as e:
            self._reset_users()
            raise e

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
        # Store the primary key of src_user, used to restore the object after
        # dry run rollback.
        self._src_user_pk = self._src_user.pk

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
                    obj.__class__, self._src_user, self._dst_user, obj,
                    reporting_strategies=self._reporting_strategies)
                handler.run()
            except ValueError:
                raise UserMergeError(
                    f'No handler for object with class {obj.__class__}.')
            except Exception as e:
                raise UserMergeError(
                    f'Failed to process object with class {obj.__class__} and '
                    f'primary key {obj.pk}. Details:\n{e}')

    def _reset_users(self):
        """Reset user objects because the values of a model's fields
        won't be reverted when a transaction rollback happens.

        Source: https://docs.djangoproject.com/en/3.2/topics/db/transactions/#controlling-transactions-explicitly
        """
        self._src_user = User.objects.get(pk=self._src_user_pk)
        self._dst_user.refresh_from_db()

    def _rollback(self):
        """Raise a UserMergeRollback exception to roll the enclosing
        transaction back."""
        raise UserMergeRollback('Rolling back.')

    def _select_users_for_update(self):
        """Block other threads from retrieving the users until the end
        of the transaction."""
        self._src_user = User.objects.select_for_update().get(
            pk=self._src_user.pk)
        self._dst_user = User.objects.select_for_update().get(
            pk=self._dst_user.pk)

    def _yield_nested_objects(self, objects):
        """Given a list that contains objects and lists of potentially-
        nested objects, return a generator that recursively yields
        objects."""
        for obj in objects:
            if isinstance(obj, list):
                yield from self._yield_nested_objects(obj)
            else:
                yield obj
