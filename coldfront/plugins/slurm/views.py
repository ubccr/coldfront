from django.shortcuts import render
from django.db.models import Q
from django.http import HttpResponse
from coldfront.core.allocation.models import Allocation

def get_slurm_accounts(request):
    if not request.user.is_authenticated:
        return HttpResponse('401 Unauthorized', status=401)

    allocation_list = Allocation.objects.filter(
        Q(status__name__in=['Active', 'Renewal Requested', ]) &
        Q(project__status__name__in=['Active']) &
        Q(project__projectuser__user=request.user) &
        Q(project__projectuser__status__name__in=['Active', ]) &
        Q(allocationuser__user=request.user) &
        Q(allocationuser__status__name__in=['Active', ])
    ).distinct()
    
    slurm_accounts = []
    for allocation in allocation_list:
        allocation_attribute_obj = allocation.allocationattribute_set.filter(
            allocation_attribute_type__name='slurm_account_name'
        )
        if allocation_attribute_obj.exists():
            slurm_account_name = allocation_attribute_obj[0].value
            resource_name = allocation.get_parent_resource.name
            project_title = allocation.project.title
            for slurm_account in slurm_accounts:
                if project_title == slurm_account.get('project_title'):
                    if slurm_account_name in slurm_account.get('slurm_account_name'):
                        slurm_account['resource_names'].append(resource_name)
                        break
            else:
                slurm_accounts.append({
                    'project_title': allocation.project.title,
                    'slurm_account_name': slurm_account_name,
                    'resource_names': [resource_name]
                })

    context = {'slurm_accounts': slurm_accounts}

    return render(request, 'slurm/slurm_account_list.html', context)