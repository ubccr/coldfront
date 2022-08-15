from coldfront.core.billing.models import BillingActivity
from coldfront.core.user.utils_.host_user_utils import lbl_email_address


def assert_identity_linking_request_serialization(identity_linking_request,
                                                  result, fields):
    """Assert that IdentityLinkingRequest serialization gives the
    expected result."""
    for field in fields:
        field_value = getattr(identity_linking_request, field)
        if field == 'requester':
            expected = str(field_value.id)
        elif field in ('request_time', 'completion_time'):
            if field_value is None:
                expected = str(field_value)
            else:
                expected = field_value.isoformat().replace('+00:00', 'Z')
        elif field == 'status':
            expected = field_value.name
        else:
            expected = str(field_value)
        actual = str(result[field])
        assert expected == actual


def assert_user_profile_serialization(user_profile, result, fields):
    """Assert that UserProfile serialization gives the expected
    result."""
    for field in fields:
        try:
            field_value = getattr(user_profile, field)
        except AttributeError:
            if field == 'host_user_lbl_email':
                expected = str(
                    lbl_email_address(user_profile.host_user)
                    if user_profile.host_user else None)
            else:
                assert False, f'Unexpected method field: {field}'
        else:
            if field == 'user':
                expected = str(field_value.id)
            elif field == 'access_agreement_signed_date':
                if field_value is None:
                    expected = str(field_value)
                else:
                    expected = field_value.isoformat().replace('+00:00', 'Z')
            elif field == 'billing_activity':
                if field_value is None:
                    expected = str(field_value)
                else:
                    expected = field_value.full_id()
            elif field == 'host_user':
                if field_value is None:
                    expected = str(field_value)
                else:
                    expected = str(field_value.id)
            else:
                expected = str(field_value)
        actual = str(result[field])
        assert expected == actual


def assert_user_serialization(user, result, fields, profile_fields):
    """Assert that User serialization gives the expected result."""
    for field in fields:
        if field == 'profile':
            assert_user_profile_serialization(
                user.userprofile, result[field], profile_fields)
        else:
            field_value = getattr(user, field)
            expected = str(field_value)
            actual = str(result[field])
            assert expected == actual
