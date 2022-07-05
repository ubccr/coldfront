from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import serializers, generics


from django.conf import settings

from coldfront.core.resource.models import ResourceAttribute, Resource
from coldfront.core.allocation.models import AllocationUser, Allocation

from coldfront.core.utils.common import import_from_settings
from coldfront.plugins.slurm.associations import SlurmCluster
from coldfront.plugins.slurm.utils import (SLURM_ACCOUNT_ATTRIBUTE_NAME,
                                           SLURM_CLUSTER_ATTRIBUTE_NAME,
                                           SLURM_USER_SPECS_ATTRIBUTE_NAME,
                                           SlurmError, slurm_remove_qos,
                                           slurm_dump_cluster, slurm_remove_account,
                                           slurm_remove_assoc)



from django.contrib.auth.models import User

from coldfront.icm.account_applications.models import AccountApplication, AccountApplicationsGIDChoice, AccountApplicationsStatusChoice
from django.shortcuts import get_object_or_404#, render


from django_auth_ldap.backend import LDAPBackend
from coldfront.plugins.ldap_user_search.utils import LDAPUserSearch
import datetime
from django.db.models.query_utils import Q

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.http import HttpResponse


class AllocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Allocation
        fields = ['id', 'all_public_attributes_as_list', 'project_id']

class SLURMAccountsAPI(APIView):
    def get(self, request, cluster):
        #resource = ResourceAttribute.objects.get(resource_attribute_type_id=15, value=cluster).resource
        resource = get_object_or_404(Resource,name=cluster)
        allocations= Allocation.objects.filter(
                resources=resource.pk, 
                status__name='Active', 
                allocationuser__user__pk=request.user.pk
        )
        return Response(AllocationSerializer(allocations, many=True).data)



@login_required
def show_auth_code(request):
    
    context = {
        'code': request.GET.get('code'),
        
    }

    return render(request, "show_code.html", context)
 