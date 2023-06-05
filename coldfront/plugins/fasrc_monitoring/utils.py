from math import isclose
from concurrent.futures import ThreadPoolExecutor

import pandas as pd
from coldfront.core.test_helpers import utils

class UIChecker:
    def __init__(self, username, password):
        self.client = utils.login_return_client(username, password)

    def check_page_loads(self, url):
        """try to load page from url with self.client.
        If successful, return response. If not, return error message.
        """
        try:
            response = self.client.get(url)
            return response
        except Exception as e:
            return str(e)

    def check_project_page(self, url):
        """Run a series of checks on project pages.
        - page loads
        - billing graph loads correctly
        """
        lines = []
        response = self.check_page_loads(url)
        if isinstance(response, str):
            lines.append({'type': 'UI', 'name': 'no_page_load', 'url': url,
                    'detail': f'{url}, {response}'})
            return lines
        if not response.context_data['time_chart_data']:
            error = response.context_data['time_chart_data_error']
            lines.append({'type': 'UI', 'name': 'no_time_chart', 'url': url,
                    'detail': f'{url}, {error}'})
        return lines

    def check_allocation_page(self, url):
        """Run checks on allocation pages.
        - page loads
        - total allocation usage doesn't exceed allocation quota
        - sum of all user usage doesn't exceed total allocation usage
        """
        lines = []
        response = self.check_page_loads(url)
        if isinstance(response, str):
            lines.append({'type': 'UI', 'name': 'no_page_load', 'url': url,
                    'detail': response})
            return lines

        # ignore inactive allocations
        if response.context_data['allocation'].status.name not in ['Active', 'New']:
            return []

        allocation_usage = response.context_data['allocation_usage_bytes']
        # flag any allocations where usage_bytes > quota_bytes
        if allocation_usage > response.context_data['allocation_quota_bytes']:
            lines.append({'type': 'Service', 'name': 'usage_over_quota', 'url': url})

        # confirm that allocation_quota_tb ~ allocation_quota_bytes
        usage_tb = response.context_data['allocation_usage_tb']
        usage_b_to_tb = allocation_usage/1099511627776
        if not isclose(usage_b_to_tb, usage_tb):
            lines.append({'type': 'Data', 'name': 'mismatched_tb_byte_usages',
                            'url': url})


        resource = response.context_data['allocation'].resources.all()[0]
        lab = response.context_data['allocation'].project
        users = response.context_data['allocation_users']._result_cache


        # add up user-level usage percentages
        user_usage_bytes_dict = {}
        user_pct_dict = {}
        for user in users:
            if user.usage_bytes and user.usage_bytes != 0:
                user_usage_bytes_dict[user.user.username] = user.usage_bytes
                if allocation_usage:
                    user_usage_pct = user.usage_bytes/allocation_usage*100
                else:
                    user_usage_pct = 200
            else:
                user_usage_pct = 0
            user_pct_dict[user.user.username] = round(user_usage_pct, 4)


        if allocation_usage:
            pct_sum = sum(user_pct_dict.values())
            bytes_sum = sum(user_usage_bytes_dict.values())
            totalpct_error_message = f'\nALLOCATION {resource} {lab} \
            percent total: {pct_sum}\ntotal usage bytes: {allocation_usage}\
            \n{user_pct_dict}\n{user_usage_bytes_dict}\n'
            if not pct_sum:
                pass
            else:
                if pct_sum > 101 and bytes_sum > allocation_usage:
                    lines.append({
                        'type': 'Data',
                        'name': 'user_usage_over_101_pct_total_usage',
                        'url': url,
                        'detail': totalpct_error_message})
                # elif pct_sum < 99 and bytes_sum != allocation_usage:
                #     lines.append({'type': 'Data',
                #         'name': 'user_usage_under_99_pct_total_usage',
                #         'detail': totalpct_error_message})
        elif sum(user.usage_bytes for user in users if user.usage_bytes is not None) > 0:
            message = f'\nALLOCATION {resource} {lab}: allocation_usage is 0 but \
             user_sum > 0\ntotal usage bytes: {allocation_usage}\n{user_pct_dict}\n{user_usage_bytes_dict}\n'
            lines.append({'type': 'Data', 'name': 'user_usage_over_101_pct_total_usage', 'url':url, 'detail': message})

        return lines


def simultaneous_checks(function, url_list, max_workers=4):
    """run a checking function on a list of urls.
    Return a combined list of the outputs. Function must return a list.
    """
    rows = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
    	# submit tasks
        for error_lines in executor.map(function, url_list):
            # report status
            rows.extend(error_lines)
    return rows

def run_view_db_checks(username, password):

    # run UI checks
    ui_checker = UIChecker(username, password)

    project_list_url = '/project/?show_all_projects=on'
    project_obj_ids = utils.collect_all_ids_in_listpage(ui_checker.client, project_list_url)
    rows = []

    project_urls = [f'/project/{obj_id}/' for obj_id in project_obj_ids]
    project_rows = simultaneous_checks(ui_checker.check_project_page, project_urls)
    rows.extend(project_rows)

    allocation_list_url = '/allocation/?show_all_allocations=on'
    allocation_obj_ids = utils.collect_all_ids_in_listpage(ui_checker.client, allocation_list_url)

    # have a separate method for collecting stats - active
    # allocations, allocations with no users, etc.
    # logger.info("number of allocation pages: %s", len(allocation_obj_ids))

    allocation_urls = [f'/allocation/{obj_id}/' for obj_id in allocation_obj_ids]
    allocation_rows = simultaneous_checks(ui_checker.check_allocation_page, allocation_urls)
    rows.extend(allocation_rows)
    df = pd.DataFrame(rows)
    df.to_csv('local_data/error_checks.csv', index=False)
