from django.contrib.auth.models import User

from flags.state import flag_enabled
from rest_framework import serializers

from coldfront.core.user.models import IdentityLinkingRequest
from coldfront.core.user.models import IdentityLinkingRequestStatusChoice
from coldfront.core.user.models import UserProfile
from coldfront.core.user.utils_.host_user_utils import host_user_lbl_email as host_user_lbl_email_method


class IdentityLinkingRequestSerializer(serializers.ModelSerializer):
    """A serializer for the IdentityLinkingRequest model."""

    status = serializers.SlugRelatedField(
        slug_field='name',
        queryset=IdentityLinkingRequestStatusChoice.objects.all())

    class Meta:
        model = IdentityLinkingRequest
        fields = (
            'id', 'requester', 'request_time', 'completion_time', 'status')
        extra_kwargs = {
            'id': {'read_only': True},
            'requester': {'read_only': True},
            'request_time': {'read_only': True},
        }


class UserProfileSerializer(serializers.ModelSerializer):
    """A serializer for the UserProfile model."""

    billing_activity = serializers.SerializerMethodField()
    host_user_lbl_email = serializers.SerializerMethodField()

    class Meta:
        model = UserProfile
        fields = (
            'id', 'user', 'is_pi', 'middle_name', 'cluster_uid',
            'phone_number', 'access_agreement_signed_date', 'billing_activity',
            'host_user', 'host_user_lbl_email')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not flag_enabled('LRC_ONLY'):
            self.fields.pop('billing_activity')
            self.fields.pop('host_user')
            self.fields.pop('host_user_lbl_email')

    @staticmethod
    def get_billing_activity(obj):
        """Return the string representation of the UserProfile's billing
        activity, or None."""
        billing_activity = obj.billing_activity
        return billing_activity.full_id() if billing_activity else None

    @staticmethod
    def get_host_user_lbl_email(obj):
        """Return the LBL email address of the User's host user, which
        may be None."""
        return host_user_lbl_email_method(obj.user)


class UserSerializer(serializers.ModelSerializer):
    """A serializer for the User model."""

    profile = UserProfileSerializer(source='userprofile', read_only=True)

    class Meta:
        model = User
        fields = (
            'id', 'username', 'first_name', 'last_name', 'email', 'profile')
