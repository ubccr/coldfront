import logging
from datetime import datetime

from django.core.management.base import BaseCommand

from coldfront.core.test_helpers import utils



datestr = datetime.today().strftime("%Y%m%d")
logger = logging.getLogger(__name__)
logger.propagate = False
logger.setLevel(logging.DEBUG)
filehandler = logging.FileHandler(f'coldfront/core/test_helpers/view_check_{datestr}.log', 'w')
logger.addHandler(filehandler)


class Command(BaseCommand):
    help = 'automatically check pages for common issues'

    def add_arguments(self, parser):
        parser.add_argument('username', nargs='+', type=str)
        parser.add_argument('password', nargs='+', type=str)

    def handle(self, *args, **options):
        username = options['username'][0]
        password = options['password'][0]
        client = utils.login_return_client(username, password)

        project_list_url = "/project/?show_all_projects=on"
        project_obj_ids = utils.collect_all_ids_in_listpage(client, project_list_url)
        utils.confirm_loads(client, project_obj_ids, "/project/")

        allocation_list_url = "/allocation/?show_all_allocations=on"
        allocation_obj_ids = utils.collect_all_ids_in_listpage(client, allocation_list_url)
        utils.confirm_loads(client, allocation_obj_ids, "/allocation/")

        stat_counter = {"no_users":0, "pct_101":0, "pct_99":0, "match": 0}
        for obj_id in allocation_obj_ids:
            url = f"/allocation/{obj_id}/"
            user_pct_dict = {}
            response = client.get(url)
            allocation_usage = response.context_data['allocation_usage_bytes']
            for user in response.context_data['allocation_users']._result_cache:
                if user.usage_bytes != 0:
                    user_usage_pct = user.usage_bytes/allocation_usage*100
                else:
                    user_usage_pct = 0
                user_pct_dict[user.user.username] = round(user_usage_pct, 4)
            pct_sum = sum(user_pct_dict.values())
            if not user_pct_dict:
                logger.warning("no user_pct_dict for %s.", obj_id)
                stat_counter["no_users"] += 1
            elif pct_sum > 101:
                logger.warning("ALLOCATION %s: pct_sum > 101. Total: %s.\n%s", obj_id, pct_sum, user_pct_dict)
                stat_counter["pct_101"] += 1
            elif sum(user_pct_dict.values()) < 99:
                logger.warning("ALLOCATION %s: pct_sum < 99. Total: %s.\n%s", obj_id, pct_sum, user_pct_dict)
                stat_counter["pct_99"] += 1
            else:
                stat_counter["match"] += 1
        logger.warning("match stats: %s", stat_counter)
