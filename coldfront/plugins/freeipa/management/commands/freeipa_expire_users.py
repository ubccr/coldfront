import logging
import os
import sys
import datetime
import dbus

from django.core.management.base import BaseCommand

from coldfront.core.allocation.models import Allocation, AllocationUser

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Report users to expire in FreeIPA'

    def add_arguments(self, parser):
        parser.add_argument(
            "-x", "--header", help="Include header in output", action="store_true")

    def write(self, data):
        try:
            self.stdout.write(data)
        except BrokenPipeError:
            devnull = os.open(os.devnull, os.O_WRONLY)
            os.dup2(devnull, sys.stdout.fileno())
            sys.exit(1)

    def handle(self, *args, **options):
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

        header = [
            'username',
            'allocation_id',
            'expire_date',
        ]

        if options['header']:
            self.write('\t'.join(header))

        bus = dbus.SystemBus()
        infopipe_obj = bus.get_object("org.freedesktop.sssd.infopipe", "/org/freedesktop/sssd/infopipe")
        ifp = dbus.Interface(infopipe_obj, dbus_interface='org.freedesktop.sssd.infopipe')


        expired_365_days_ago = datetime.datetime.today() - datetime.timedelta(days=365)

        expired_365_days_ago = expired_365_days_ago.date()
        # Find all active users on active allocations
        active_users = sorted(list(set(AllocationUser.objects.filter(allocation__project__status__name__in=[
            'Active', 'New'], allocation__status__name='Active', status__name='Active').values_list('user__username', flat=True))))

        # Find all user in expired allocations
        expired_allocation_users = {}
        for allocation in Allocation.objects.filter(status__name='Expired'):
            for allocationuser in allocation.allocationuser_set.all():
                if allocationuser.user.username in active_users:
                    continue

                if allocationuser.user.username not in expired_allocation_users:
                    expired_allocation_users[allocationuser.user.username] = {
                        'expire_date': allocation.end_date,
                        'allocation_id': allocation.id
                    }
                else:
                    if allocation.end_date > expired_allocation_users[allocationuser.user.username]['expire_date']:
                        expired_allocation_users[allocationuser.user.username] = {
                            'expire_date': allocation.end_date,
                            'allocation_id': allocation.id
                        }

        # Print users whose latest allocation expiration date GTE 365 days and active in FreeIPA
        for key in expired_allocation_users.keys():
            if expired_allocation_users[key]['expire_date'] < expired_365_days_ago:
                try:
                    result = ifp.GetUserAttr(key, ["nsaccountlock"])
                    if 'nsAccountLock' in result and str(result['nsAccountLock'][0]) == 'TRUE':
                        # User is already disabled in FreeIPA so do nothing
                        pass
                    else:
                        # User is active in FreeIPA but not on any active allocations
                        self.write('\t'.join([
                            key,
                            str(expired_allocation_users[key]['allocation_id']),
                            expired_allocation_users[key]['expire_date'].strftime("%Y-%m-%d")
                        ]))
                except dbus.exceptions.DBusException as e:
                    if 'No such user' in str(e):
                        logger.info("User %s not found in FreeIPA", key)
                    else:
                        logger.error("dbus error failed to find user %s in FreeIPA: %s", key, e)
