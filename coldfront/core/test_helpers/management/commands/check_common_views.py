from django.core.management.base import BaseCommand

from coldfront.core.test_helpers import utils

class Command(BaseCommand):
    help = 'automatically check pages for common issues'

    def add_arguments(self, parser):
        parser.add_argument('username', nargs='+', type=str)
        parser.add_argument('password', nargs='+', type=str)

    def handle(self, *args, **options):
        username = options['username'][0]
        password = options['password'][0]
        client = utils.login_return_client(username, password)
        utils.confirm_loads(client, "/project/?show_all_projects=on")
        utils.confirm_loads(client, "/allocation/?show_all_allocations=on")

        obj_ids = utils.collect_all_ids_in_listpage(client, "/allocation/?show_all_allocations=on")
        for obj_id in obj_ids:
            url = f"/allocation/{obj_id}/"
            user_pct_dict = {}
            response = client.get(url)
            allocation_usage = response.context_data['allocation_usage_bytes']
            for user in response.context_data['allocation_users']._result_cache:
                if user.usage_bytes != 0:
                    user_usage_pct = user.usage_bytes/allocation_usage*100
                else:
                    user_usage_pct = 0
                user_pct_dict[user] = user_usage_pct
            pct_sum = sum(user_pct_dict.values())
            if not user_pct_dict:
                print(f"no user_pct_dict for {obj_id}.")
            elif pct_sum > 101:
                print(f"ALLOCATION {obj_id}: pct_sum > 100. Total: {pct_sum}.\n{user_pct_dict}")
            elif sum(user_pct_dict.values()) < 99:
                print(f"ALLOCATION {obj_id}: pct_sum < 99. Total: {pct_sum}.\n{user_pct_dict}")
