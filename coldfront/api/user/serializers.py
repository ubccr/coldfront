from coldfront.core.user.models import IdentityLinkingRequest
from coldfront.core.user.models import IdentityLinkingRequestStatusChoice
from django.contrib.auth.models import User
from rest_framework import serializers


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


class UserSerializer(serializers.ModelSerializer):
    """A serializer for the User model."""

    class Meta:
        model = User
        fields = ('id', 'username', 'first_name', 'last_name', 'email')
