from datetime import datetime, timedelta
from pathlib import Path
from coldfront.core.utils.common import import_from_settings
from coldfront.core.utils.local_utils import read_json, save_json
from coldfront.plugins.sftocf.pipeline.basepipeline import UsageDataPipelineBase
from coldfront.plugins.sftocf.utils import record_process
from starfish_api_client import StarfishAPIClient
import logging

logger = logging.getLogger(__name__)
SFDATAPATH = import_from_settings('SFDATAPATH')
svp = read_json('coldfront/plugins/sftocf/servers.json')

PENDING_ACTIVE_ALLOCATION_STATUSES = import_from_settings(
    'PENDING_ACTIVE_ALLOCATION_STATUSES', ['Active', 'New', 'In Progress', 'On Hold'])

class RESTDataPipeline(UsageDataPipelineBase):
    """Collect data from Starfish's REST API to update Coldfront Allocations."""

    def return_connection_obj(self, sfserver):
        return StarfishAPIClient(sfserver)

    @record_process
    def produce_lab_dict(self):
        """Create dict of lab/volume combinations to collect and the volumes associated with them.
        Parameters
        ----------
        vol : string
            If not None, collect only allocations on the specified volume
        Returns
        -------
        labs_resources: dict
            Structured as follows:
            'lab_name': [('volume', 'path'), ('volume', 'path')]
        """
        pr_objs = self.allocations.only('id', 'project')
        labs_resources = {allocation.project.title: [] for allocation in pr_objs}
        for allocation in pr_objs:
            proj_name = allocation.project.title
            resource = allocation.get_parent_resource
            if resource:
                vol_name = resource.name.split('/')[0]
            else:
                message = f'no resource for allocation owned by {proj_name}'
                print(message)
                logger.error(message)
                continue
            if resource not in self.volumes:
                continue
            if allocation.path:
                labs_resources[proj_name].append((vol_name, allocation.path))
        return labs_resources

    def check_volume_collection(self, lr):
        """
        for each lab-resource combination in parameter lr, check existence of
        corresponding file in data path. If a file for that lab-resource
        combination that is <2 days old exists, mark it as collected. If not,
        slate lab-resource combination for collection.

        Parameters
        ----------
        lr : dict
            Keys are labnames, values are a list of (volume, tier) tuples.

        Returns
        -------
        filepaths : list
            List of lab usage files that have already been created.
        to_collect : list
            list of tuples - (labname, volume, tier, filename)
        """
        filepaths = []
        to_collect = []
        labs_resources = [(l, res) for l, r in lr.items() for res in r]
        logger.debug('labs_resources:%s', labs_resources)

        yesterdaystr = (datetime.today()-timedelta(1)).strftime("%Y%m%d")
        dates = [yesterdaystr, DATESTR]

        for lr_pair in labs_resources:
            lab = lr_pair[0]
            resource = lr_pair[1][0]
            path = lr_pair[1][1]
            fpath = f"{SFDATAPATH}{lab}_{resource}_{path.replace('/', '_')}.json"
            if Path(fpath).exists():
                file_json = read_json(fpath)
                if file_json['date'] in dates:
                    filepaths.append(fpath)
            else:
                to_collect.append((lab, resource, path, fpath,))
        return filepaths, to_collect

    def return_usage_query_data(self, usage_query):
        try:
            data = usage_query.result
            if not data:
                logger.warning('No starfish result for usage_query %s', usage_query)
        except ValueError as err:
            logger.warning('error with query: %s', err)
            data = None
        return data

    @property
    def items_to_pop(self):
        return ['size_sum_hum', 'rec_aggrs', 'physical_nlinks_size_sum',
            'physical_nlinks_size_sum_hum', 'volume_display_name', 'count', 'fn']

    def collect_sf_user_data(self):
        """Collect starfish data using the REST API. Return the results."""
        # 1. produce dict of all labs to be collected & volumes on which their data is located
        lab_res = self.produce_lab_dict()
        # 2. produce list of files collected & list of lab/volume/filename tuples to collect
        filepaths, to_collect = self.check_volume_collection(lab_res)
        # 3. produce set of all volumes to be queried
        vol_set = {i[1] for i in to_collect}
        vols = [vol for vol in vol_set if vol in svp['volumes']]
        for volume in vols:
            projects = [t for t in to_collect if t[1] == volume]
            logger.debug('vol: %s\nto_collect_subset: %s', volume, projects)

            ### OLD METHOD ###
            for tup in projects:
                p = tup[0]
                filepath = tup[3]
                lab_volpath = tup[2] #volumepath[0] if '_l3' not in p else volumepath[1]
                logger.debug('filepath: %s lab: %s volpath: %s', filepath, p, lab_volpath)
                usage_query = self.connection_obj.create_query(
                    f'groupname={p} type=f',
                    'volume,username,groupname',
                    f'{volume}:{lab_volpath}',
                )
                data = self.return_usage_query_data(usage_query.result)
                if data:
                    contents = [d for d in data if d['username'] != 'root']
                    for entry in contents:
                        # entry['size_sum'] = entry['rec_aggrs']['size']
                        # entry['full_path'] = entry['parent_path']+'/'+entry['fn']
                        for item in self.items_to_pop:
                            entry.pop(item, None)
                    record = {
                        'server': self.connection_obj.name,
                        'volume': volume,
                        'path': lab_volpath,
                        'project': p,
                        'date': datetime.today().strftime('%Y%m%d'),
                        'contents': contents,
                    }
                    save_json(filepath, record)
                    filepaths.append(filepath)

        collected_data = []
        for filepath in filepaths:
            content = read_json(filepath)
            for user in content['contents']:
                user.update({
                    'volume': content['volume'],
                    'path': content['path'],
                    'project': content['project'],
                })
                collected_data.append(user)
        return collected_data

    def collect_sf_usage_data(self):
        """Collect usage data from starfish for all labs in the lab list."""
        # 1. produce dict of all labs to be collected & volumes on which their data is located
        lab_res = self.produce_lab_dict()
        lab_res = [(k, i[0], i[1]) for k, v in lab_res.items() for i in v]
        # 2. produce set of all volumes to be queried
        vol_set = {i[1] for i in lab_res}
        vols = [vol for vol in vol_set if vol in svp['volumes']]
        entries = []
        for volume in vols:
            volumepath = svp['volumes'][volume]
            projects = [t for t in lab_res if t[1] == volume]
            logger.debug('vol: %s\nto_collect_subset: %s', volume, projects)

            ### OLD METHOD ###
            for tup in projects:
                p = tup[0]
                lab_volpath = volumepath[0] if '_l3' not in p else volumepath[1]
                logger.debug('lab: %s volpath: %s', p, lab_volpath)
                usage_query = self.connection_obj.create_query(
                    f'groupname={p} type=d depth=1',
                    'volume,parent_path,groupname,rec_aggrs.size,fn',
                    f'{volume}:{lab_volpath}',
                    qformat='parent_path +aggrs.by_gid',
                )
                data = self.return_usage_query_data(usage_query.result)
                if data:
                    if len(data) > 1:
                        logger.error('too many data entries for %s: %s', p, data)
                        continue
                    entry = data[0]
                    entry.update({
                        'size_sum': entry['rec_aggrs']['size'],
                        'full_path': entry['parent_path']+'/'+entry['fn'],
                        'server': self.connection_obj.name,
                        'volume': volume,
                        'path': lab_volpath,
                        'project': p,
                        'date': datetime.today().strftime('%Y%m%d'),
                    })
                    for item in self.items_to_pop:
                        entry.pop(item)
                    entries.append(entry)
        return entries
