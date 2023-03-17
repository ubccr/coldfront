import logging
from datetime import datetime
from math import isclose

from django.core.management.base import BaseCommand

from coldfront.core.test_helpers import utils

datestr = datetime.today().strftime('%Y%m%d')
logger = logging.getLogger(__name__)
logger.propagate = False
logger.setLevel(logging.DEBUG)
filehandler = logging.FileHandler(f'logs/view_check_{datestr}.log', 'w')
logger.addHandler(filehandler)


def report_errors(error_dict):
    for k, v in error_dict.items():
        errors = len(v) - 1
        if errors:
            logger.warning('\n\n%s count: %s', k, errors)
            message = ''.join(v)
            logger.warning(message)


class Command(BaseCommand):
    help = 'automatically check pages for common issues'

    def add_arguments(self, parser):
        parser.add_argument('username', nargs='+', type=str)
        parser.add_argument('password', nargs='+', type=str)

    def handle(self, *args, **options):
        username = options['username'][0]
        password = options['password'][0]
        client = utils.login_return_client(username, password)

        logger.warning('Project page error checks')
        project_list_url = '/project/?show_all_projects=on'
        project_obj_ids = utils.collect_all_ids_in_listpage(client, project_list_url)
        project_errors = {
                'no_page_load': ['Project page load fails:\n'],
                'no_time_chart': ['Time chart load fails:\n']}
        for obj_id in project_obj_ids:
            url = f'/project/{obj_id}/'
            try:
                response = client.get(url)
            except Exception as e:
                project_errors['no_page_load'].append(f'Failed load for url: {url}   {e}\n{e.__traceback__}')
                continue
            if not response.context_data['time_chart_data']:
                project_errors['no_time_chart'].append(f"{obj_id}, ")
        report_errors(project_errors)


        logger.warning('Allocation page error checks')
        allocation_list_url = '/allocation/?show_all_allocations=on'
        allocation_obj_ids = utils.collect_all_ids_in_listpage(client, allocation_list_url)

        allocation_errors = {
            'no_page_load': ['Allocation page load fails:\n'],
            'usage_over_quota': ['allocations with usage_bytes > quota_bytes:\n'],
            'mismatched_usages': ['allocations with mismatched byte-tb usage\n'],
            'inactive': ['inactive allocations:\n'],
            'no_users': ['allocations with no users:\n'],
            'pct_101': ['groups with pct_sum > 101:\n'],
            'pct_99': ['groups with pct_sum < 99:\n']
            }

        logger.info("number of allocation pages: %s", len(allocation_obj_ids))
        for obj_id in allocation_obj_ids:
            url = f'/allocation/{obj_id}/'
            try:
                response = client.get(url)
            except Exception as e:
                allocation_errors['no_page_load'].append(f'Failed load for url: {url}   {e}\n{e.__traceback__}')
                continue
            user_usage_bytes_dict = {}
            user_pct_dict = {}
            if response.context_data['allocation'].status.name not in ['Active', 'New']:
                allocation_errors['inactive'].append(f"{obj_id}, ")
                continue
            allocation_usage = response.context_data['allocation_usage_bytes']
            # flag any allocations where usage_bytes > quota_bytes
            if allocation_usage > response.context_data['allocation_quota_bytes']:
                allocation_errors['usage_over_quota'].append(f"{obj_id}, ")
            # confirm that allocation_quota_tb ~ allocation_quota_bytes
            usage_tb = response.context_data['allocation_usage_tb']
            usage_b_to_tb = allocation_usage/1099511627776
            if not isclose(usage_b_to_tb, usage_tb):
                allocation_errors['mismatched_usages'].append(f'{obj_id} ({usage_b_to_tb} v. {usage_tb})\n')
            # confirm that allocation_usage_tb < allocation_quota_tb

            resource = response.context_data['allocation'].resources.all()[0]
            lab = response.context_data['allocation'].project
            users = response.context_data['allocation_users']._result_cache

            for user in users:
                if user.usage_bytes and user.usage_bytes != 0:
                    user_usage_bytes_dict[user.user.username] = user.usage_bytes
                    if allocation_usage != 0:
                        user_usage_pct = user.usage_bytes/allocation_usage*100
                    else:
                        user_usage_pct = 200
                else:
                    user_usage_pct = 0
                user_pct_dict[user.user.username] = round(user_usage_pct, 4)


            if allocation_usage != 0:
                pct_sum = sum(user_pct_dict.values())
                bytes_sum = sum(user_usage_bytes_dict.values())
                totalpct_error_message = f'\nALLOCATION {obj_id} {resource} {lab} \
                percent total: {pct_sum}\ntotal usage bytes: {allocation_usage}\
                \n{user_pct_dict}\n{user_usage_bytes_dict}\n'
                if not user_pct_dict:
                    logger.warning('no user_pct_dict for %s.', obj_id)
                    allocation_errors['no_users'].append(f"{obj_id}, ")
                elif pct_sum == 0 and allocation_usage == 0:
                    continue
                elif pct_sum > 101:
                    allocation_errors['pct_101'].append(totalpct_error_message)
                    if bytes_sum <= allocation_usage:
                        message = f"NON-ISSUE FOR {obj_id} {resource} {lab}\npercent total: {pct_sum}\ntotal usage bytes: {allocation_usage}\n{user_pct_dict}\n{user_usage_bytes_dict}\n"
                        logger.warning(message)
                elif pct_sum < 99:
                    allocation_errors['pct_99'].append(totalpct_error_message)
                    if bytes_sum == allocation_usage:
                        logger.warning("NON-ISSUE")
            elif sum(user.usage_bytes for user in users if user.usage_bytes is not None) > 0:
                allocation_errors['pct_101'].append(f'\nALLOCATION {obj_id} \
                {resource} {lab}: allocation_usage is 0 but user_sum > 0\ntotal \
                usage bytes: {allocation_usage}\n{user_pct_dict}\n{user_usage_bytes_dict}\n')
        report_errors(allocation_errors)
