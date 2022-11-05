from rest_framework import serializers

from coldfront.core.billing.models import BillingActivity
from coldfront.core.billing.models import BillingProject


class BillingActivitySerializer(serializers.ModelSerializer):
    """A serializer for the BillingActivity model."""

    billing_project = serializers.SlugRelatedField(
        slug_field='identifier', queryset=BillingProject.objects.all())

    class Meta:
        model = BillingActivity
        fields = ('id', 'billing_project', 'identifier')
