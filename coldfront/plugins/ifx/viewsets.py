# -*- coding: utf-8 -*-

'''
Viewsets
'''
from ifxbilling.serializers import BillingRecordViewSet, ProductUsageViewSet
from rest_framework.authentication import TokenAuthentication
from ifxreport.serializers import ReportRunViewSet
from coldfront.plugins.ifx.permissions import FiineBillingRecordViewSetPermissions, AdminPermissions

class ColdfrontBillingRecordViewSet(BillingRecordViewSet):
    '''
    Set FiineOrAdmin permisisons
    '''
    permission_classes = [FiineBillingRecordViewSetPermissions]
    authentication_classes = [TokenAuthentication]
    pagination_class = None


class ColdfrontReportRunViewSet(ReportRunViewSet):
    '''
    Set Admin permissions
    '''
    permission_classes = [AdminPermissions]
#    authentication_classes = [TokenAuthentication]
    pagination_class = None

class ColdfrontProductUsageViewSet(ProductUsageViewSet):
    '''
    Set FiineOrAdmin permisisons
    '''
    permission_classes = [AdminPermissions]
#    authentication_classes = [TokenAuthentication]
    pagination_class = None