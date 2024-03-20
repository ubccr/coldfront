'''tests for Isilon plugin'''

from coldfront.core.allocation.models import Allocation, AllocationStatusChoice
from coldfront.core.project.models import Project
from coldfront.core.resource.models import Resource
from coldfront.plugins.isilon.utils import IsilonConnection, create_isilon_allocation_quota


def test_create_isilon_allocation_quota():
    """test create_isilon_connection
    uses cftest_lab to test
    """
    # create dummy allocation for cftest_lab
    allocation = Allocation(
        project=Project.objects.get(title='cftest_lab'),
        status=AllocationStatusChoice.objects.get(name='New'),
    )

    path = f'ifs/rc_labs/{allocation.project.title}'
    # for each isilon cluster:
    for resource in Resource.objects.filter(name__contains='tier1'):
        # create isilon IsilonConnection
        isilon_connection = IsilonConnection(resource.name)
        # run create_isilon_allocation_quota on the allocation with the isilon cluster
        create_isilon_allocation_quota(allocation, resource)

        # check that the directory acl is properly created
        acl = isilon_connection.namespace_client.get_acl(
            namespace_path=path,
            acl=True,
        )
        # confirm that acl mode is 2770
        assert acl.mode == '2770'
        # confirm that 
        print(acl)
        # check that the directory quota is properly created
        quota_list = isilon_connection.quota_client.list_quota_quotas()
        quota = next(q for q in quota_list.quotas if q.path == f'/{path}')
        assert quota.thresholds.hard == 1099511627776
        print(quota)

        # check that the snapshot schedule is properly created
        schedules = isilon_connection.snapshot_client.list_snapshot_schedules()
        snapshot_schedule = next(
            s for s in schedules.schedules if s.path == f'/{path}')
        print(snapshot_schedule)

        # check that the nfs export is properly created
        exports = isilon_connection.nfs_client.list_nfs_exports()
        export = next(e for e in exports.exports if e.path == f'/{path}')
        print(export)
        # check that the smb share is properly created
        shares = isilon_connection.smb_client.list_smb_shares()
        share = next(s for s in shares.shares if s.path == f'/{path}')
        print(share)
        
        # delete the quota
        isilon_connection.quota_client.delete_quota_quota(
            path=f'/{path}',
        )


        # delete the directory
        isilon_connection.namespace_client.delete_directory(path)

