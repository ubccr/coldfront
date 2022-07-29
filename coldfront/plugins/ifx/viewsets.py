# -*- coding: utf-8 -*-

'''
Viewsets
'''
from ifxbilling.serializers import BillingRecordViewSet
from rest_framework.authentication import TokenAuthentication
from coldfront.plugins.ifx.permissions import FiineBillingRecordViewSetPermissions

class ColdfrontBillingRecordViewSet(BillingRecordViewSet):
    '''
    Set FiineOrAdmin permisisons
    '''
    permission_classes = [FiineBillingRecordViewSetPermissions]
    authentication_classes = [TokenAuthentication]
    pagination_class = None