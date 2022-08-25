# -*- coding: utf-8 -*-

'''
Calculate Coldfront billing records for the given year and month
'''
import logging
import os
from textwrap import TextWrapper
from collections import defaultdict
from django.utils import timezone
from django.core.management.base import BaseCommand
from coldfront.plugins.ifx.calculator import NewColdfrontBillingCalculator


logger = logging.getLogger('ifxbilling')


class Command(BaseCommand):
    '''
    Calculate Coldfront billing records for the given year and month
    '''
    help = 'Calculate Coldfront billing records for the given year and month.  Use --recalculate to remove existing records and recreate. Usage:\n' + \
        "./manage.py newCalculateBillingRecords --year 2021 --month 3"

    def add_arguments(self, parser):
        parser.add_argument(
            '--year',
            dest='year',
            default=timezone.now().year,
            help='Year for calculation',
        )
        parser.add_argument(
            '--month',
            dest='month',
            default=timezone.now().month,
            help='Month for calculation',
        )
        parser.add_argument(
            '--recalculate',
            action='store_true',
            help='Remove existing billing records and recalculate',
        )

    def handle(self, *args, **kwargs):
        month = int(kwargs['month'])
        year = int(kwargs['year'])
        recalculate = kwargs['recalculate']
        verbosity = kwargs.get('verbosity', 1) - 1
        if verbosity < 0:
            verbosity = 0
        bc = NewColdfrontBillingCalculator()
        results = bc.calculate_billing_month(year, month, recalculate=recalculate, verbosity=verbosity)

        error_groups = defaultdict(list)
        output = {}
        for org, result in results.items():
            successes = result[0]
            errors = result[1]
            if not successes and len(errors) == 1:  # No successes
                if 'No project found' in errors[0]:
                    error_groups['No project found'].append(org)
                else:
                    output[org] = result
            elif not successes and not errors:  # Has project, but no active allocations
                error_groups['No charges'].append(org)
            else:
                output[org] = result

        if error_groups:
            for key, labs in error_groups.items():
                print(f'\n{key}:\n\t', end='')
                print('\n\t'.join(sorted(labs)))
        if output:
            print_report(output, get_terminal_size())

def print_report(output, terminalsize):
    """
    Print a report
    """
    if terminalsize == 0:
        terminalsize = 80

    # Total width of terminal text
    width = terminalsize - 2

    # Margin on either side of long text
    textmargin = 6

    # Width to pass to TextWrapper
    textwidth = width - textmargin * 2

    # Setup the text wrapper
    descwrapper = TextWrapper(width=textwidth, initial_indent=" " * textmargin, subsequent_indent=" " * (textmargin + 2))


    for lab in sorted(output.keys()):
        reportlines= []
        if output[lab][0]:
            successstr = '''
{lab}
{brlines}
            '''.format(
                lab=lab,
                brlines='\n'.join([descwrapper.fill(str(br)) for br in output[lab][0]]),
            )
            reportlines.append(successstr)
        if output[lab][1]:
            errorstr = '''
{lab} Errors:
{errorlines}
            '''.format(
                lab=lab,
                errorlines=descwrapper.fill('\n'.join(output[lab][1])),
            )
            reportlines.append(errorstr)

        print(''.join(reportlines))

def get_terminal_size():
    '''
    Get the size of the terminal
    '''
    env = os.environ

    def ioctl_GWINSZ(fd):
        try:
            import fcntl, termios, struct, os
            cr = struct.unpack("hh", fcntl.ioctl(fd, termios.TIOCGWINSZ, "1234"))
        except Exception:
            return
        return cr
    cr = ioctl_GWINSZ(0) or ioctl_GWINSZ(1) or ioctl_GWINSZ(2)
    if not cr:
        try:
            fd = os.open(os.ctermid(), os.O_RDONLY)
            cr = ioctl_GWINSZ(fd)
            os.close(fd)
        except Exception:
            pass
    if not cr:
        cr = (env.get("LINES", 25), env.get("COLUMNS", 80))

    return int(cr[1])
