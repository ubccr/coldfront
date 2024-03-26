from django.shortcuts import render
from django.http import HttpResponse
from coldfront.core.allocation.models import Allocation
from coldfront.core.allocation.models import Project
from coldfront.core.utils.common import import_from_settings

SLURM_SUBMISSION_INFO = import_from_settings('SLURM_SUBMISSION_INFO', ['account'])
SLURM_DISPLAY_SHORT_OPTION_NAMES = import_from_settings('SLURM_DISPLAY_SHORT_OPTION_NAMES', False)
SLURM_SHORT_OPTION_NAMES = import_from_settings('SLURM_SHORT_OPTION_NAMES', {})


def get_all_slurm_submission_info(request):
    if not request.user.is_authenticated:
        return HttpResponse('401 Unauthorized', status=401)

    project_list = Project.objects.filter(
        status__name='Active',
        projectuser__user=request.user,
        projectuser__status__name='Active',
    )

    project_titles = {}
    slurm_submission_info = {}
    for project_obj in project_list:
        project_titles[project_obj.pk] = project_obj.title
        slurm_submission_info[project_obj.pk] = []
        allocation_list = project_obj.allocation_set.filter(
            status__name__in=['Active', 'Renewal Requested', ],
            allocationuser__user=request.user,
            allocationuser__status__name='Active',
        )
        for allocation_obj in allocation_list:
            slurm_submission_info[project_obj.pk].append(get_slurm_submission_info_from_allocation(allocation_obj))

    context = {}
    context['slurm_submission_info'] = slurm_submission_info
    context['project_titles'] = project_titles
    return render(request, 'slurm/all_slurm_submission_info.html', context)


def get_slurm_submission_info(request):
    allocation_obj = Allocation.objects.get(pk=request.POST.get('allocation_pk'))
    slurm_submission_info = get_slurm_submission_info_from_allocation(allocation_obj)
    return render(request, 'slurm/slurm_submission_info.html', {'slurm_submission_info': slurm_submission_info})


def get_slurm_submission_info_from_allocation(allocation_obj):
    submit_options = {}
    resource_obj = allocation_obj.get_parent_resource
    resource_type = resource_obj.resource_type.name
    if resource_type == 'Cluster Partition':
        cluster_obj = resource_obj.parent_resource
        if 'clusters' in SLURM_SUBMISSION_INFO:
            submit_options['clusters'] = cluster_obj.resourceattribute_set.get(resource_attribute_type__name='slurm_cluster').value
        if 'partition' in SLURM_SUBMISSION_INFO:
            submit_options['partition'] = resource_obj.name.lower()
    elif resource_type != 'Cluster':
        return {}

    slurm_account = allocation_obj.allocationattribute_set.filter(allocation_attribute_type__name='slurm_account_name')
    if slurm_account.exists():
        if 'account' in SLURM_SUBMISSION_INFO:
            submit_options['account'] = slurm_account[0].value

    slurm_specs = resource_obj.resourceattribute_set.filter(resource_attribute_type__name='slurm_specs')
    submit_options = get_slurm_submission_info_from_slurm_specs(slurm_specs, submit_options)
    slurm_specs = allocation_obj.allocationattribute_set.filter(allocation_attribute_type__name='slurm_specs')
    submit_options = get_slurm_submission_info_from_slurm_specs(slurm_specs, submit_options)

    if SLURM_DISPLAY_SHORT_OPTION_NAMES:
        submit_short_options = {}
        for option, value in submit_options.items():
            short_option = SLURM_SHORT_OPTION_NAMES.get(option)
            if short_option:
                submit_short_options['-' + short_option] = value
            else:
                submit_short_options['--' + option] = value

        slurm_submission_info = submit_short_options
    else:
        submit_long_options = {}
        for option, value in submit_options.items():
            submit_long_options['--' + option] = value

        slurm_submission_info = submit_long_options

    return {resource_obj.name: slurm_submission_info}


def get_slurm_submission_info_from_slurm_specs(slurm_specs, submit_options):
    if slurm_specs.exists():
        specs = slurm_specs[0].value.replace('+', '').split(':')
        for spec in specs:
            spec_split = spec.split('=')
            # Expanded attributes should be skipped
            if len(spec_split) > 2:
                continue
            option, value = spec_split
            option = option.lower()
            if option in SLURM_SUBMISSION_INFO:
                submit_options[option] = value

    return submit_options