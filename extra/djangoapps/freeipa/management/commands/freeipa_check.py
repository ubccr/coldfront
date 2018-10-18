import logging
import os
import sys

from django.core.management.base import BaseCommand, CommandError

from core.djangoapps.subscription.models import Subscription
from ipalib import api
from ipalib.errors import NotFound
from extra.djangoapps.freeipa.utils import check_ipa_group_error, CLIENT_KTNAME, \
                                           FREEIPA_NOOP, UNIX_GROUP_ATTRIBUTE_NAME

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Sync groups in FreeIPA'

    def add_arguments(self, parser):
        parser.add_argument("-s", "--sync", help="Sync changes to/from FreeIPA", action="store_true")
        parser.add_argument("-u", "--username", help="Check specific username")
        parser.add_argument("-g", "--group", help="Check specific group")
        parser.add_argument("-x", "--header", help="Include header in output", action="store_true")

    def check_ipa_error(self, res):
        if not res or 'result' not in res:
            raise ValueError('Missing FreeIPA result')

    def add_group(self, userobj, group, status):
        if self.sync and not FREEIPA_NOOP:
            try:
                res = api.Command.group_add_member(group, user=[userobj.user.username])
                check_ipa_group_error(res)
            except Exception as e:
                logger.error("Failed adding user %s to group %s: %s", userobj.user.username, group, e)
            else:
                logger.info("Added user %s to group %s successfully", userobj.user.username, group)

        row = [
            userobj.user.username,
            str(userobj.subscription.id),
            userobj.status.name,
            group,
            '',
            status,
            'Active' if userobj.user.is_active else 'Inactive',
        ]

        self.stdout.write('\t'.join(row))

    def remove_group(self, userobj, group, status):
        if self.sync and not FREEIPA_NOOP:
            try:
                res = api.Command.group_remove_member(group, user=[userobj.user.username])
                check_ipa_group_error(res)
            except Exception as e:
                logger.error("Failed removing user %s from group %s: %s", userobj.user.username, group, e)
            else:
                logger.info("Removed user %s from group %s successfully", userobj.user.username, group)

        row = [
            userobj.user.username,
            str(userobj.subscription.id),
            userobj.status.name,
            '',
            group,
            status,
            'Active' if userobj.user.is_active else 'Inactive',
        ]

        self.stdout.write('\t'.join(row))

    def sync_user_status(self, userobj, active=False):
        if not self.sync:
            return

        if FREEIPA_NOOP:
            return

        try:
            userobj.user.is_active = active
            userobj.user.save()
        except Exception as e:
            logger.error('Failed to update user status: %s - %s', userobj.user.username, e)

    def check_user(self, userobj, groups):
        logger.info("Checking user %s in subscription %s for group membership: %s", userobj.user.username, userobj.subscription, groups)

        freeipa_groups = []
        freeipa_status = 'Unknown'
        try:
            res = api.Command.user_show(userobj.user.username)
            logger.debug(res)
            self.check_ipa_error(res)
            for g in res['result'].get('memberof_group', ()):
                freeipa_groups.append(g)
            for g in res['result'].get('memberofindirect_group', ()):
                freeipa_groups.append(g)

            if res['result'].get('nsaccountlock', False):
                freeipa_status = 'Disabled'
            else:
                freeipa_status = 'Enabled'

        except NotFound as e:
            logger.warn("User %s not found in FreeIPA", userobj.user.username)
            freeipa_status = 'NotFound'
        except Exception as e:
            logger.error("Failed to find user %s in FreeIPA: %s", userobj.user.username, e)
            return

        for g in groups:
            if userobj.status.name == 'Active' and g not in freeipa_groups:
                logger.warn('Active user %s not in freeipa group: %s', userobj.user.username, g)
                self.add_group(userobj, g, freeipa_status)
            elif userobj.status.name == 'Removed' and g in freeipa_groups:
                logger.warn('Removed user %s still in freeipa group: %s', userobj.user.username, g)
                self.remove_group(userobj, g, freeipa_status)

        if freeipa_status == 'Disabled' and userobj.user.is_active:
            logger.warn('User is active in coldfront but disabled in FreeIPA: %s', userobj.user.username)
            self.sync_user_status(userobj, active=False)
        elif freeipa_status == 'Enabled' and not userobj.user.is_active:
            logger.warn('User is not active in coldfront but enabled in FreeIPA: %s', userobj.user.username)
            self.sync_user_status(userobj, active=True)

    def handle(self, *args, **options):
        os.environ["KRB5_CLIENT_KTNAME"] = CLIENT_KTNAME

        verbosity = int(options['verbosity'])
        root_logger = logging.getLogger('')
        if verbosity == 0:
            root_logger.setLevel(logging.ERROR)
        elif verbosity == 2:
            root_logger.setLevel(logging.INFO)
        elif verbosity == 3:
            root_logger.setLevel(logging.DEBUG)
        else:
            root_logger.setLevel(logging.WARN)

        self.sync = False
        if options['sync']:
            self.sync = True
            logger.warn("Syncing Coldfront with FreeIPA")

        header = [
            'username',
            'subscription_id',
            'subscription_status',
            'add_missing_freeipa_group_membership',
            'remove_existing_freeipa_group_membership',
            'freeipa_status',
            'coldfront_status',
        ]

        if options['header']:
            self.stdout.write('\t'.join(header))

        # Fetch all active subscriptions with a 'freeipa_group' attribute
        subs = Subscription.objects.prefetch_related(
                'project',
                'resources',
                'subscriptionattribute_set',
                'subscriptionuser_set'
            ).filter(
                status__name='Active',
                subscriptionattribute__subscription_attribute_type__name=UNIX_GROUP_ATTRIBUTE_NAME,
            ).distinct()

        logger.info("Processing %s active subscriptions with %s attribute", len(subs), UNIX_GROUP_ATTRIBUTE_NAME)
        if options['username']:
            logger.info("Filtering output by username: %s", options['username'])
        if options['group']:
            logger.info("Filtering output by group: %s", options['group'])

        for s in subs:
            groups = s.get_attribute_list(UNIX_GROUP_ATTRIBUTE_NAME)
            if options['group']:
                if options['group'] not in groups:
                    continue
                else:
                    groups = [options['group']]
                        
            for u in s.subscriptionuser_set.filter(status__name__in=['Active', 'Removed', ]):
                if options['username'] and options['username'] != u.user.username:
                    continue

                self.check_user(u, groups)
