import logging

from drf_yasg import openapi
from rest_framework import mixins
from rest_framework import viewsets

from coldfront.api.billing.serializers import BillingActivitySerializer
from coldfront.api.permissions import IsSuperuserOrStaff
from coldfront.core.billing.models import BillingActivity


logger = logging.getLogger(__name__)


authorization_parameter = openapi.Parameter(
    'Authorization',
    openapi.IN_HEADER,
    description=(
        'The authorization token for the requester. The token should be '
        'preceded by "Token " (no quotes).'),
    type=openapi.TYPE_STRING)


class BillingActivityViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin,
                             viewsets.GenericViewSet):
    """A ViewSet for the BillingActivity model."""

    permission_classes = [IsSuperuserOrStaff]
    serializer_class = BillingActivitySerializer

    def get_queryset(self):
        return BillingActivity.objects.order_by('id')
