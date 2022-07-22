def assert_cluster_access_request_serialization(cluster_access_request,
                                                      result, fields):
    """Assert that ClusterAccessRequest serialization gives the
    expected result."""
    for field in fields:
        if field == 'id':
            expected = str(cluster_access_request.pk)
        elif field == 'status':
            expected = cluster_access_request.status.name
        elif field == 'completion_time':
            field_value = getattr(cluster_access_request, field)
            if field_value is None:
                expected = str(field_value)
            else:
                expected = field_value.isoformat().replace('+00:00', 'Z')
        elif field == 'allocation_user':
            assert_allocation_user_serialization(cluster_access_request.allocation_user,
                                                 result['allocation_user'],
                                                 ('id', 'allocation', 'user', 'project', 'status'))
            continue
        elif field == 'billing_activity':
            try:
                expected = str(cluster_access_request.billing_activity.full_id)
            except AttributeError:
                expected = str(None)
        actual = str(result[field])

        assert expected == actual


def assert_allocation_user_serialization(allocation_user, result, fields):
    """Assert that AllocationUser serialization gives the
    expected result."""
    for field in fields:
        if field == 'id':
            expected = str(allocation_user.pk)
        elif field == 'allocation':
            expected = str(allocation_user.allocation.pk)
        elif field == 'user':
            expected = allocation_user.user.username
        elif field == 'project':
            expected = allocation_user.allocation.project.name
        elif field == 'status':
            expected = allocation_user.status.name
        else:
            raise AssertionError('Invalid Field Passed')
        actual = str(result[field])

        assert expected == actual