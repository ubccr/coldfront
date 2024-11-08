from coldfront.plugins.sftocf.pipeline.basepipeline import UsageDataPipelineBase
from starfish_api_client import RedashAPIClient

class RedashDataPipeline(UsageDataPipelineBase):
    """Collect data from Redash to update Coldfront Allocations."""

    def return_connection_obj(self, sfhost):
        # 1. grab data from redash
        return RedashAPIClient(sfhost, query_id, REDASH_KEY)

    def collect_sf_user_data(self):
        """Collect starfish data using the Redash API. Return the results."""
        user_usage = self.connection_obj.return_query_results(
            query='path_usage_query', volumes=self.volumes
        )
        for d in user_usage:
            d['username'] = d.pop('user_name')
            d['volume'] = d.pop('vol_name')
            d['path'] = d.pop('lab_path')
        return user_usage

    def collect_sf_usage_data(self):
        allocation_usage = self.connection_obj.return_query_results(
            query='subdirectory', volumes=self.volumes
        )
        for d in allocation_usage:
            d['username'] = d.pop('user_name')
            d['volume'] = d.pop('vol_name')
        return allocation_usage

    def collect_sf_data_for_lab(self, lab_name, volume_name):
        """Collect user-level and allocation-level usage data for a specific lab."""
        lab_allocation_data = [d for d in self.sf_usage_data if d['group_name'] == lab_name and d['volume'] == volume_name]
        if len(lab_allocation_data) > 1:
            raise ValueError("more than one allocation for this lab/volume combination")
        lab_user_data = [d for d in self.sf_user_data if d['volume'] == volume_name and d['path'] == lab_allocation_data[0]['path']]
        return lab_user_data, lab_allocation_data

