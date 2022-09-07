def assert_billing_activity_serialization(billing_activity, result, fields):
    """Assert that BillingActivity serialization gives the expected
    result."""
    for field in fields:
        field_value = getattr(billing_activity, field)
        if field == 'billing_project':
            expected = billing_activity.billing_project.identifier
        else:
            expected = str(field_value)
        actual = str(result[field])
        assert expected == actual
