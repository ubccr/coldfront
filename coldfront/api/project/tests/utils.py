def assert_project_user_removal_request_serialization(removal_request,
                                                      result, fields):
    """Assert that ProjectUserRemovalRequest serialization gives the
    expected result."""
    for field in fields:
        if field == 'id':
            expected = str(removal_request.pk)
        elif field == 'status':
            expected = removal_request.status.name
        elif field in ('request_time', 'completion_time'):
            field_value = getattr(removal_request, field)
            if field_value is None:
                expected = str(field_value)
            else:
                expected = field_value.isoformat().replace('+00:00', 'Z')
        elif field == 'project_user':
            assert_project_user_serialization(removal_request.project_user,
                                              result['project_user'],
                                              ('id', 'user', 'project', 'role', 'status'))
            continue
        actual = str(result[field])
        assert expected == actual


def assert_project_user_serialization(project_user, result, fields):
    """Assert that ProjectUser serialization gives the
    expected result."""
    for field in fields:
        if field == 'id':
            expected = str(project_user.pk)
        elif field == 'user':
            expected = project_user.user.username
        elif field == 'project':
            expected = project_user.project.name
        elif field == 'role':
            expected = project_user.role.name
        elif field == 'status':
            expected = project_user.status.name
        else:
            raise AssertionError('Invalid Field Passed')
        actual = str(result[field])
        assert expected == actual
