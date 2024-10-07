import textwrap

from coldfront.config.env import ENV
from coldfront.core.utils.mail import EMAIL_ENABLED, send_email

def acl_reset_complete_hook(task_object):
    task_duration = '{:.2f}'.format(task_object.time_taken())
    allocation_name = task_object.args[1].get_attribute('storage_name')
    recipient = task_object.args[0]
    subject = f'{allocation_name} ACL Reset Task'
    email_body = ''
    if task_object.success:
        email_body += textwrap.fill(
            (
                'Your request to perform an ACL Reset '
                f'(task "{task_object.name}") on allocation "{allocation_name}" '
                f'completed successfully after {task_duration} seconds.'
            ),
            width=80
        )
    else:
        email_body += textwrap.fill(
            (
                'Your request to perform an ACL Reset '
                f'(task {task_object.name})\n on allocation {allocation_name} '
                f'failed after {task_duration} seconds.  The error returned '
                f'was: {task_object.result}.'
            ),
            width=80
        )
    email_body += (
        '\n\n'
        'If you need anything further, then please contact User Support.'
        '\n\n'
        'Thanks,\n\n'
        'Coldfront\n\n'
    )
    if EMAIL_ENABLED:
        send_email(
            subject,
            (
                'Greetings,\n\n'
                f'{email_body}'
            ),
            'ris@wustl.edu',
            [recipient]
        )
    else:
        log_file = ENV.str(
            'ACL_RESET_MSG_LOG',
            default='/tmp/e-mail_notifications.log'
        )
        with open(log_file, 'a') as emnl:
            emnl.write(
                (
                    f'To: {task_object.args[0]}\n'
                    'From: Coldfront <coldfront@coldfront.com>\n'
                    f'Subject: {subject}\n\nGreetings,\n\n'
                    f'{email_body}'
                    '######################################################\n'
                )
            )

