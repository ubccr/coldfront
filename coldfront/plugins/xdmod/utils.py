import logging
import requests
import json
import xml.etree.ElementTree as ET
import re
import sys

from coldfront.core.utils.common import import_from_settings
from coldfront.core.organization.models import (
        OrganizationLevel,
        Organization,
        OrganizationProject,
        )
from coldfront.core.allocation.models import (
        Allocation,
        AllocationAttribute,
        )
from coldfront.plugins.slurm.utils import (
        SLURM_ACCOUNT_ATTRIBUTE_NAME,
        allocations_with_slurm_accounts,
        )
from django.contrib.auth.models import User


XDMOD_CLOUD_PROJECT_ATTRIBUTE_NAME = import_from_settings('XDMOD_CLOUD_PROJECT_ATTRIBUTE_NAME', 'Cloud Account Name')
XDMOD_CLOUD_CORE_TIME_ATTRIBUTE_NAME = import_from_settings('XDMOD_CLOUD_CORE_TIME_ATTRIBUTE_NAME', 'Core Usage (Hours)')
XDMOD_ACCOUNT_ATTRIBUTE_NAME = import_from_settings('XDMOD_ACCOUNT_ATTRIBUTE_NAME', 'slurm_account_name')
XDMOD_RESOURCE_ATTRIBUTE_NAME = import_from_settings('XDMOD_RESOURCE_ATTRIBUTE_NAME', 'xdmod_resource')
XDMOD_CPU_HOURS_ATTRIBUTE_NAME = import_from_settings('XDMOD_CPU_HOURS_ATTRIBUTE_NAME', 'Core Usage (Hours)')
XDMOD_API_URL = import_from_settings('XDMOD_API_URL')

# Maximum number of tiers/levels in hierarchy supported by XdMod
XDMOD_MAX_HIERARCHY_TIERS  = import_from_settings(
        'XDMOD_MAX_HIERARCHY_TIERS', 3)
# Booleans.  If set, allocation and/or project appears in XdMod hierarchy
XDMOD_ALLOCATION_IN_HIERARCHY = import_from_settings(
        'XDMOD_ALLOCATION_IN_HIERARCHY', False)
XDMOD_PROJECT_IN_HIERARCHY = import_from_settings(
        'XDMOD_PROJECT_IN_HIERARCHY', False)
# Info and label fields to use in hierarchy.json for Allocation or Project tier
XDMOD_ALLOCATION_HIERARCHY_LABEL = import_from_settings(
        'XDMOD_ALLOCATION_HIERARCHY_LABEL', 'Allocation')
XDMOD_ALLOCATION_HIERARCHY_INFO = import_from_settings(
        'XDMOD_ALLOCATION_HIERARCHY_INFO', 'Allocation')
XDMOD_PROJECT_HIERARCHY_LABEL = import_from_settings(
        'XDMOD_PROJECT_HIERARCHY_LABEL', 'Project')
XDMOD_PROJECT_HIERARCHY_INFO = import_from_settings(
        'XDMOD_PROJECT_HIERARCHY_INFO', 'Project')
# If XDMOD_ALLOCATION_IN_HIERARCHY is set, look for these AllocationAttributes
# for the naming the generated hierachy entries
XDMOD_ALLOCATION_HIERARCHY_CODE_ATTRIBUTE_NAME = import_from_settings(
    'XDMOD_ALLOCATION_HIERARCHY_CODE_ATTRIBUTE_NAME', 'xdmod_alloc_code')
XDMOD_ALLOCATION_HIERARCHY_NAME_ATTRIBUTE_NAME = import_from_settings(
    'XDMOD_ALLOCATION_HIERARCHY_NAME_ATTRIBUTE_NAME', 'xdmod_alloc_name')
# If XDMOD_ALLOCATION_IN_HIERARCHY is set and the above AllocationAttributes
# are not set, use the slurm_account_name with following prefix/suffix
XDMOD_ALLOCATION_HIERARCHY_CODE_PREFIX = import_from_settings(
    'XDMOD_ALLOCATION_HIERARCHY_CODE_PREFIX', '')
XDMOD_ALLOCATION_HIERARCHY_CODE_SUFFIX = import_from_settings(
    'XDMOD_ALLOCATION_HIERARCHY_CODE_SUFFIX', '')
# If XDMOD_PROJECT_IN_HIERARCHY is set, these are used for naming of the
# Project level hierarchy entries
XDMOD_PROJECT_HIERARCHY_CODE_MODE = import_from_settings(
    'XDMOD_PROJECT_HIERARCHY_CODE_MODE', 'pi_username')
XDMOD_PROJECT_HIERARCHY_CODE_PREFIX = import_from_settings(
    'XDMOD_PROJECT_HIERARCHY_CODE_PREFIX', '')
XDMOD_PROJECT_HIERARCHY_CODE_SUFFIX = import_from_settings(
    'XDMOD_PROJECT_HIERARCHY_CODE_SUFFIX', '')
XDMOD_PROJECT_HIERARCHY_CODE_ATTRIBUTE_NAME = import_from_settings(
    'XDMOD_PROJECT_HIERARCHY_CODE_ATTRIBUTE_NAME', 'xdmod_project_code')
# These control the first_name and last_name fields for XdMod names.csv
# for Users.  The string is processed with the Python format() method,
# passing arguments fname, lname, username, email for the User's 
# first_name, last_name, username, and email fields.
# If None, will default to '{fname}' for FNAME and '{lname}' for LNAME
XDMOD_NAMES_CSV_USER_FNAME_FORMAT = import_from_settings(
    'XDMOD_NAMES_CSV_USER_FNAME_FORMAT', '{fname}')
XDMOD_NAMES_CSV_USER_LNAME_FORMAT = import_from_settings(
    'XDMOD_NAMES_CSV_USER_LNAME_FORMAT', '{lname}')


_ENDPOINT_CORE_HOURS = '/controllers/user_interface.php'

_DEFAULT_PARAMS = {
    'aggregation_unit': 'Auto',
    'display_type': 'bar',
    'format': 'xml',
    'operation': 'get_data',
    'public_user': 'true',
    'query_group': 'tg_usage',
}

logger = logging.getLogger(__name__)

class XdmodError(Exception):
    pass

class XdmodNotFoundError(XdmodError):
    pass

def xdmod_fetch_total_cpu_hours(start, end, account, resources=None):
    if resources is None:
        resources = []

    url = '{}{}'.format(XDMOD_API_URL, _ENDPOINT_CORE_HOURS)
    payload = _DEFAULT_PARAMS
    payload['pi_filter'] = '"{}"'.format(account)
    payload['resource_filter'] = '"{}"'.format(','.join(resources))
    payload['start_date'] = start
    payload['end_date'] = end
    payload['group_by'] = 'pi'
    payload['realm'] = 'Jobs'
    payload['operation'] = 'get_data'
    payload['statistic'] = 'total_cpu_hours'
    r = requests.get(url, params=payload)

    logger.info(r.url)
    logger.info(r.text)

    try:
        error = r.json()
        # XXX fix me. Here we assume any json response is bad as we're
        # expecting xml but XDMoD should just return json always. 
        raise XdmodNotFoundError('Got json response but expected XML: {}'.format(error))
    except json.decoder.JSONDecodeError as e:
        pass

    try:
        root = ET.fromstring(r.text)
    except ET.ParserError as e:
        raise XdmodError('Invalid XML data returned from XDMoD API: {}'.format(e))

    rows = root.find('rows')
    if len(rows) != 1:
        raise XdmodNotFoundError('Rows not found for {} - {}'.format(account, resources))

    cells = rows.find('row').findall('cell')
    if len(cells) != 2:
        raise XdmodError('Invalid XML data returned from XDMoD API: Cells not found')

    core_hours = cells[1].find('value').text

    return core_hours

def xdmod_fetch_cloud_core_time(start, end, project, resources=None):
    if resources is None:
        resources = []

    url = '{}{}'.format(XDMOD_API_URL, _ENDPOINT_CORE_HOURS)
    payload = _DEFAULT_PARAMS
    payload['project_filter'] = project
    payload['resource_filter'] = '"{}"'.format(','.join(resources))
    payload['start_date'] = start
    payload['end_date'] = end
    payload['group_by'] = 'project'
    payload['realm'] = 'Cloud'
    payload['operation'] = 'get_data'
    payload['statistic'] = 'cloud_core_time'
    r = requests.get(url, params=payload)

    logger.info(r.url)
    logger.info(r.text)

    try:
        error = r.json()
        # XXX fix me. Here we assume any json response is bad as we're
        # expecting xml but XDMoD should just return json always. 
        raise XdmodNotFoundError('Got json response but expected XML: {}'.format(error))
    except json.decoder.JSONDecodeError as e:
        pass

    try:
        root = ET.fromstring(r.text)
    except ET.ParserError as e:
        raise XdmodError('Invalid XML data returned from XDMoD API: {}'.format(e))

    rows = root.find('rows')
    if len(rows) != 1:
        raise XdmodNotFoundError('Rows not found for {} - {}'.format(project, resources))

    cells = rows.find('row').findall('cell')
    if len(cells) != 2:
        raise XdmodError('Invalid XML data returned from XDMoD API: Cells not found')

    core_hours = cells[1].find('value').text

    return core_hours

def xdmod_orglevel_hierarchy_list():
    """This method a list of XdMod hierarchy levels, from bottom/leaf to 
    top/root.

    This method returns a list describing the XdMod hierarchy levels.  The
    first element in the returned list is the bottom-most/leaf level, and the
    last if the top-most/root level.  The elements of the list are either
    instnaces of class OrganizationLevel, and/or the strings 'project' or
    'allocation'.

    The length of the list will be at most XDMOD_MAX_HIERARCHY_TIERS; if there
    are so many OrganizationLevels with export_to_xdmod set that this limit will
    be exceeded, we prune on the top-most/root side.

    The strings 'allocation' and 'project' will only occur if the booleans
    XDMOD_ALLOCATION_IN_HIERARCHY and XDMOD_PROJECT_IN_HIERARCHY, respectively, 
    are true.  Because Organizations are assigned to projects, any hierarchical
    tiers from OrganizationLevels are higher/closer to top-most/root tier, so 
    the 'allocation' tier, if present, will always appear first, and the 
    'project', if present, will either be first (if no 'allocation' tier), or 
    immediately follow the 'allocation' tier.  The remaining tiers will be 
    taken from OrganizationLevels with export_to_xdmod set, until we run out 
    of OrganizationLevels or reach XDMOD_MAX_HIERARCHY_TIERS tiers.
    """
    # This is ordered root to leaf
    org_level_hier = OrganizationLevel.generate_orglevel_hierarchy_list(
            validate=False)
    # Remove OrganizationLevels which do not export_to_xdmod
    org_level_hier = [ x for x in org_level_hier if x.export_to_xdmod ]

    if XDMOD_PROJECT_IN_HIERARCHY:
        org_level_hier.append('project')
    if XDMOD_ALLOCATION_IN_HIERARCHY:
        org_level_hier.append('allocation')

    # Remove any orglevels that exceed XDMOD_MAX_HIERARCHY_TIERS, from 
    # root side
    max = XDMOD_MAX_HIERARCHY_TIERS
    excess = len(org_level_hier) - max
    if excess > 0:
        org_level_hier = org_level_hier[excess:]

    # We reverse to get in leaf to root order
    org_level_hier.reverse()
    return org_level_hier

def generate_xdmod_orglevel_hierarchy_setup():
    """This method generates an XdMod hierarchy.json data structure.

    This generates a Python dictionary with the data suitable
    for use as the source for the hierarchy.json file describing
    the levels of the XdMod hierarchy.

    If XDMOD_ALLOCATION_IN_HIERARCHY is set/true, then the bottom-most/leaf
    tier will be described by XDMOD_ALLOCATION_HIERARCHY_LABEL and
    XDMOD_ALLOCATION_HIERARCHY_INFO.  If XDMOD_PROJECT_IN_HIERARCHY then either
    the bottom-most/leaf (if XDMOD_ALLOCATION_IN_HIERARCHY not set) or the next 
    lowest tier will be set to XDMOD_PROJECT_HIERARCHY_LABEL and 
    XDMOD_PROJECT_HIERARCHY_INFO.  The remaining tiers will be filled with the
    lowest level (bottom/leaf-most) OrganizationLevels with export_to_xdmod set.

    *** This routine does *NOT* use XDMOD_MAX_HIERARCHY_TIERS ***
    It is currently restricted to exactly 3 tiers based on the format of the
    hierarchy.json file.  If XDMOD_MAX_HIERARCHY_TIERS exceeds this, we truncate
    dropping the higher/top-most/most-root-like tiers.  If we do not fill out
    the 3 tiers, we put dummy text in the higher tiers to fill it out.

    Return value is a dictionary which can be used to generate hierarchy.json.
    """
    org_level_hier = xdmod_orglevel_hierarchy_list()
    hier_dict = {}

    xdmod_levels = [ 'bottom', 'middle', 'top' ]
    num_xdmod_levels = len(xdmod_levels)
    if len(org_level_hier) > num_xdmod_levels:
        # We only know how to handle num_xdmod_levels tiers, so truncate
        # any exccess
        org_level_hier = org_level_hier[0:num_xdmod_levels-1]

    i = 0
    for orglev in org_level_hier:
        label = None
        info = None
        if orglev == 'allocation':
            label = XDMOD_ALLOCATION_HIERARCHY_LABEL
            info = XDMOD_ALLOCATION_HIERARCHY_INFO
        elif orglev == 'project':
            label = XDMOD_PROJECT_HIERARCHY_LABEL
            info = XDMOD_PROJECT_HIERARCHY_INFO
        else:
            # We must have an OrganizationLevel
            label = orglev.name
            info = orglev.name

        xdmod_level = xdmod_levels[i]
        hier_dict['{}_level_label'.format(xdmod_level)] = label
        hier_dict['{}_level_info'.format(xdmod_level)] = info
        i = i + 1

    # Put dummy entries on any remaining hierarchy levels
    while i < num_xdmod_levels:
        hier_dict['{}_level_label'.format(xdmod_level)] = 'Not used'
        hier_dict['{}_level_info'.format(xdmod_level)] = 'Not used'

    return hier_dict

def xdmod_hier_code_for_project(project):
    """This returns the code and name for hierarchy.csv for an project.

    This is only used if XDMOD_PROJECT_IN_HIERARCHY is set/true, and 
    will return the code, name and parent for the specified project
    (which is assumed to have an Allocation with AllocationAttribute of type 
    given by the value of SLURM_ACCOUNT_ATTRIBUTE_NAME).  

    The name returned will be the title of the Project.  

    The value for the code depends on the setting of 
    XDMOD_PROJECT_HIERARCHY_CODE_MODE which can take one or more of the
    following values (multiple values should be delimitted by commas, and
    will be processed left to right, with the first entry producing a value
    having effect):
        'pi_username': The basename will be the username of the PI
        '-slurm_account_name': The basename will be found by taking the 
            slurm_account_name of all Allocations under the Project, and then
            taking the first in lexical order.
        '+slurm_account_name': Like '-slurm_account_name', but take the last
            in lexical order.
        'title': The Project title will be used as the basename.  Any 
            characters which are not alphanumeric or hypen/underscore will 
            be converted to underscores.
        'attribute': We will search all Allocations belonging to the Project
            and see if any have an AllocationAttribute with type given by the
            value of XDMOD_PROJECT_HIERARCHY_CODE_ATTRIBUTE_NAME, and if so
            use the value of that attribute as the basename.  If no such 
            AllocationAttribute is found, we pass to the next mode in the list.
            If multiple allocations have that attribute set, we use the
            one associated with allocation with the lowest pk (you really 
            should ensure all have the same value of the attribute in this
            case).
    Of the above, only the value 'attribute' can allow passing to the next
    mode in the list.  If XDMOD_PROJECT_HIERARCHY_CODE_MODE does not have a
    value, or we run out of modes before getting a value, we will default
    to 'pi_username'.
    
    Unless the basename was set via the 'attribute' mode, it will then
    be prefixed/suffixed by the strings from the
    XDMOD_PROJECT_HIERARCHY_CODE_PREFIX and XDMOD_PROJECT_HIERARCHY_CODE_SUFFIX
    to produce the final 'code'.  For the 'attribute' mode case, the basename
    becomes the code w/out any additional prefix/suffix.

    Returns the tuple code, name
    """
    name = project.title
    code = None

    modes = []
    if XDMOD_PROJECT_HIERARCHY_CODE_MODE:
        modes = XDMOD_PROJECT_HIERARCHY_CODE_MODE.split(',')
    modes.append('pi_username')

    basename = None
    noprefixsuffix = False
    for mode in modes:
        if mode == 'pi_username':
                basename = project.pi.username
                break

        if mode == 'title':
            basename = project.title
            basename = re.sub('[^a-zA-Z_-]', '_', basename)
            break

        if mode == 'attribute':
            if XDMOD_PROJECT_HIERARCHY_CODE_ATTRIBUTE_NAME is None:
                # If the var is not defined, then we ignore this mode
                continue

        # -slurm_account_name/+slurm_account_name/attribute all are based
        # on Allocations belonging to the Project
        allocs = Allocation.objects.filter(project=project)

        if mode == 'attribute':
            tmp = AllocationAttribute.objects.filter(
                    allocation__project=project,
                    allocation_attribute_type__name=
                    XDMOD_PROJECT_HIERARCHY_CODE_ATTRIBUTE_NAME).order_by(
                            'allocation__pk')
            if tmp:
                basename = tmp[0].value
                noprefixsuffix = True
                break
            continue
            
        # slurm_account_name variants all want AllocationAttributes with
        # of type given by SLURM_ACCOUNT_ATTRIBUTE_NAME.  
        tmp = AllocationAttribute.objects.filter(
                allocation__project=project,
                allocation_attribute_type__name=SLURM_ACCOUNT_ATTRIBUTE_NAME)
        slurm_acct_names = list(map(lambda x: x.value, tmp))
        slurm_acct_names.sort()
        if mode == '-slurm_account_name' or mode == 'slurm_account_name':
            basename = slurm_acct_names[0]
        elif mode == '+slurm_account_name':
            basename = slurm_acct_names[-1]
        else:
            raise ValueError('Illegal value {} in '
                    'XDMOD_PROJECT_HIERARCHY_CODE_MODE'.format(mode))
        break
    #end for mode in modes:

    if noprefixsuffix:
        code = basename
    else:
        prefix = ''
        suffix = ''
        if XDMOD_PROJECT_HIERARCHY_CODE_PREFIX:
            prefix = XDMOD_PROJECT_HIERARCHY_CODE_PREFIX
        if XDMOD_PROJECT_HIERARCHY_CODE_SUFFIX:
            suffix = XDMOD_PROJECT_HIERARCHY_CODE_SUFFIX
        code = '{}{}{}'.format(prefix, basename, suffix)

    return code, name

def xdmod_hier_code_for_allocation(allocation, account_name=None):
    """This returns the code and name for hierarchy.csv for an allocation.

    This is only used if XDMOD_ALLOCATION_IN_HIERARCHY is set/true, and 
    will return the code, name and parent for the specified allocation 
    (which is assumed to have an AllocationAttribute of type given by the
    value of SLURM_ACCOUNT_ATTRIBUTE_NAME).  

    The code will be the value of the attribute with type given by the
    value of XDMOD_ALLOCATION_HIERARCHY_CODE_ATTRIBUTE_NAME, if present.
    Otherwise the code will be generated from the account_name (either as 
    provided or from the value of the attribute with
    type given by SLURM_ACCOUNT_ATTRIBUTE_NAME) with the fixed values 
    XDMOD_ALLOCATION_HIERARCHY_CODE_PREFIX and 
    XDMOD_ALLOCATION_HIERARCHY_CODE_SUFFIX strings prefixed/suffixed.

    The name will be the value of the attribute with type given by the value
    of XDMOD_ALLOCATION_HIERARCHY_NAME_ATTRIBUTE_NAME, if present, or will
    default to being the same as the value for the code.

    Returns the tuple code, name
    """
    code = None
    name = None
    if XDMOD_ALLOCATION_HIERARCHY_CODE_ATTRIBUTE_NAME:
        tmp = AllocationAttribute.objects.filter(
                allocation_attribute_type__name=
                XDMOD_ALLOCATION_HIERARCHY_CODE_ATTRIBUTE_NAME,
                allocation=allocation)
        if tmp:
            code = tmp[0].value

    if code is None:
        if account_name is None:
            tmp = AllocationAttribute.objects.filter(
                allocation_attribute_type__name=SLURM_ACCOUNT_ATTRIBUTE_NAME,
                allocation=allocation)
            account_name = tmp[0].value
        base = account_name
        prefix = ''
        suffix = ''
        if XDMOD_ALLOCATION_HIERARCHY_CODE_PREFIX:
            prefix = XDMOD_ALLOCATION_HIERARCHY_CODE_PREFIX
        if XDMOD_ALLOCATION_HIERARCHY_CODE_SUFFIX:
            suffix = XDMOD_ALLOCATION_HIERARCHY_CODE_SUFFIX
        code = '{}{}{}'.format(prefix,base,suffix)

    if XDMOD_ALLOCATION_HIERARCHY_NAME_ATTRIBUTE_NAME:
        tmp = AllocationAttribute.objects.filter(
                allocation_attribute_type__name=
                XDMOD_ALLOCATION_HIERARCHY_NAME_ATTRIBUTE_NAME,
                allocation=allocation)
        if tmp:
            name = tmp[0].value

    if name is None:
        name = code

    return code, name

def generate_xdmod_org_hierarchy():
    """This method generates an XdMod hierarchy.csv data structure.

    This generates a Python list describing the XdMod hierarchy, suitable for
    producing the hierarchy.csv file.  The list describes the organizations/etc
    in the XdMod hierarchy, and will have elements which are
    triplets of the form (code, name, parent_code) where code is an unique code
    for the organization, name is a more descriptive name, and parent_code is 
    the code for the parent organization (or None if there is no parent).

    If XDMOD_ALLOCATION_IN_HIERARCHY is set/true, then the bottom-most/leaf tier
    will be the allocation.  This setting is for if you wish to consolidate 
    several allocations into a single unit in xdmod beneath the Project level.  
    In this case, we search for all Allocations which have an 
    AllocationAttribute of type slurm_account_name (or actually the value of
    SLURM_ACCOUNT_ATTRIBUTE_NAME) and call xdmod_hier_code_for_allocation
    on the allocation to get the hierarchy code and name.  If
    XDMOD_PROJECT_IN_HIERARCHY is set, then the parent will be the project
    containing the allocation (using the code generated by 
    xdmod_hier_code_for_project), or the primary_organization or first ancestor
    of that organization which is exported to XdMod.

    If XDMOD_PROJECT_IN_HIERARCHY is set/true, then the next lowest tier 
    will be the project. This is for if you wish to consolidate all of the 
    allocations in the same Project into a single xdmod hierarchical unit.
    In this case, for any Project which has an Allocation
    which has an Attribute of type SLURM_ACCOUNT_ATTRIBUTE_NAME, we will 
    generate an entry for the Project.  The code and name will be set by the
    method xdmod_hier_code_for_project, see that method for details).

    The return list consists of triplet n-tupels (code, name, parent) (where 
    parent may be None if no parent), and is ordered so that the higher level 
    Orgs come first.  
    """
    org_level_hier = xdmod_orglevel_hierarchy_list()
    hier_list = []
    last_orglev = None
    exported_org_by_org = {}

    nexti = 0
    for orglev in org_level_hier:
        hier_list_for_olev = []
        nexti = nexti + 1
        if nexti < len(org_level_hier):
            nextorglev = org_level_hier[nexti]
        else:
            nextorglev = None

        projs_hash = None
        if orglev == 'allocation':
            alist = allocations_with_slurm_accounts(orderby=['allocation__pk'])
            handled_by_code = {}
            for arec in alist:
                alloc = arec['allocation']
                aname = arec['account_name']
                code, name = xdmod_hier_code_for_allocation(alloc, aname)
                if code in handled_by_code:
                    # Already processed an allocation with this code
                    continue #for arec in alist
                else:
                    handled_by_code[code] = name
                # Now need the parent
                if XDMOD_PROJECT_IN_HIERARCHY:
                    # Parent is project containing alloc
                    proj = alloc.project
                    pcode, pname = xdmod_hier_code_for_project(proj)
                    if projs_hash is None:
                        projs_hash = {}
                    projs_hash[proj] = {
                            'project': proj,
                            'code': pcode,
                            'name': pname,
                            }
                    parent = pcode
                    if nextorglev is None:
                        parent = None
                else: #if XDMOD_PROJECT_IN_HIERARCHY
                    # Next level is not project, so we want primary_org of
                    # project, or first ancestor exported to xdmod
                    proj = alloc.project
                    org = OrganizationProject.get_primary_organization_for_project(
                            proj)
                    if org is not None:
                        xdmod_org = org.next_xdmod_exported_organization()
                        if xdmod_org is None:
                            parent = None
                        else:
                            parent = xdmod_org.fullcode()
                        exported_org_by_org[org] = xdmod_org
                        if nextorglev is None:
                            parent = None
                    else: #if org is not None 
                        parent = None
                    # end: if org is not None
                    if projs_hash is None:
                        projs_hash = {}
                    projs_hash[proj] = {
                            'project': proj,
                            'parent': parent,
                            }
                # end: if XDMOD_PROJECT_IN_HIERARCHY
                hier_list_for_olev.append( (code, name, parent) )
            # End for arec in alist
            # prepend elements of hier_list_for_ovel to hier_list
            hier_list[:0] = hier_list_for_olev
            continue # for orglev in org_level_hier:
        elif orglev == 'project': #if orglev == 'allocation':
            if projs_hash is None:
                # Previous org level was not 'allocation'
                # So we start from scratch
                projs_hash = {}
                alist = allocations_with_slurm_accounts(
                        orderby=['allocation__project__pi__username', 
                            'allocation__project__title'])
                for arec in alist:
                    alloc = arec['allocation']
                    proj = alloc.project
                    if proj in projs_hash:
                        # We already handled this Project
                        continue
                    code, name = xdmod_hier_code_for_project(proj)
                    org = OrganizationProject.get_primary_organization_for_project(proj)
                    if org is None:
                        parent = None
                    elif org in exported_org_by_org: #if org is None
                        parent_org = exported_org_by_org[org]
                        if parent_org is None:
                            parent = None
                        else:
                            parent = parent_org.fullcode()
                    else: #if org is None
                        parent_org = org.next_xdmod_exported_organization()
                        exported_org_by_org[org] = parent_org
                        if parent_org is None:
                            parent = None
                        else:
                            parent = parent_org.fullcode()
                    # end: if org is None
                    if nextorglev is None:
                        parent = None
                    hier_list_for_olev.append( (code, name, parent) )
                    projs_hash[proj] = (code, name, parent)
                #end: for arec in alist
            else: #if projs_hash is None
                # Previous org level was 'allocation', so a lot of work
                # already done
                if projs_hash is None:
                    # No projects to add
                    continue # for orglev in org_level_hier:
                for key, prec in projs_hash.items():
                    proj = prec['project']
                    if code in prec:
                        code = prec['code']
                        name = prec['name']
                        org = OrganizationProject.get_primary_organization_for_project(proj)
                        if org is None:
                            parent = None
                        elif org in exported_org_by_org: #if org is None
                            parent_org = exported_org_by_org[org]
                            if parent_org is None:
                                parent = None
                            else:
                                parent = parent_org.fullcode()
                        else: #if org is None
                            parent_org = org.next_xdmod_exported_organization()
                            exported_org_by_org[org] = parent_org
                            if parent_org is None:
                                parent = None
                        # end if org is None
                        if nextorglev is None:
                            parent = None
                        hier_list_for_olev.append( (code, name, parent) )
                    else: #if code in prec
                        parent = prec['parent']
                        code, name = xdmod_hier_code_for_project(proj)
                    #end if code in prec
                    hier_list_for_olev.append( (code, name, parent) )
                #end for key, prec in projs_hash.items()
            #end if projs_hash is None
            # prepend elements of hier_list_for_ovel to hier_list
            hier_list[:0] = hier_list_for_olev
            continue # for orglev in org_level_hier:
        else: #if orglev == 'allocation':
            # orglev is an OrganizationLevel
            # Find all Organizations at this OrganizationLevel
            orgs = Organization.objects.filter(organization_level=orglev)
            for org in orgs:
                code = org.fullcode()
                name = org.shortname
                parent_org = org.parent
                if parent_org is None:
                    parent = None
                elif parent_org in exported_org_by_org: #if parent_org is None
                    porg = exported_org_by_org[parent_org]
                    if porg is None:
                        parent = None
                    else:
                        parent = porg.fullcode()
                    if nextorglev is None:
                        parent = None
                else: #if parent_org is None
                    porg = parent_org.next_xdmod_exported_organization()
                    if porg is None:
                        parent = None
                    else:
                        exported_org_by_org[parent_org] = porg
                        parent = porg.fullcode()
                #end if parent_org is None
                if nextorglev is None:
                    parent = None
                hier_list_for_olev.append( (code, name, parent) )
            #end for org in orgs
            # prepend elements of hier_list_for_ovel to hier_list
            hier_list[:0] = hier_list_for_olev
            continue # for orglev in org_level_hier:
    # End for orglev in org_level_hier:
    return hier_list

def generate_xdmod_group_to_hierarchy():
    """This method generates an XdMod groups-to-hierarchy.csv data structure.

    This generates a Python list with the data relating Slurm allocation
    accounts to the XdMod organizational hierarchy, which can be used for
    the generation of the XdMod groups-to-hierarchy.csv file.

    We examine all Allocations with an slurm_account_name (i.e.
    SLURM_ACCOUNT_ATTRIBUTE_NAME) AllocationAttribute, and then determine
    the lowest Organization in the Project's primary organizational parentage
    which is at a OrganizationalLevel  exported to XdMod.  We then append
    a doublet (2-tuple) (slurm_account_name, orgfullcode) to the list we
    will return.
    """
    org_level_hier = xdmod_orglevel_hierarchy_list()
    orglev = list(org_level_hier)[0]
    group_list = []

    alist = allocations_with_slurm_accounts()
    for arec in alist:
        alloc = arec['allocation']
        aname = arec['account_name']

        if orglev == 'allocation':
            code, name = xdmod_hier_code_for_allocation(alloc)
            group_list.append( (aname, code) )
        elif orglev == 'project':
            proj = alloc.project
            code, name = xdmod_hier_code_for_project(proj)
            group_list.append( (aname, code) )
        else:
            proj = alloc.project
            org = OrganizationProject.get_primary_organization_for_project(proj)
            if org is not None:
                parent_org = org.next_xdmod_exported_organization()
                if parent_org is None:
                    code = None
                else:
                    code = parent_org.fullcode()
            group_list.append( (aname, code) )

    return group_list

def generate_xdmod_names_for_users():
    """This method generates usernames to names for XdMod names.csv

    This generates a Python list with the data relating usernames to
    real names which can be used for generating the names.csv file.
    The elements of the list are triplets of form (username, first_name,
    last_name).

    We produce an entry for all User objects which have an username set,
    and the username will be used in the username elements.  The first_name
    and last_name elements are generated according to the values of
    XDMOD_NAMES_CSV_USER_FNAME_FORMAT and XDMOD_NAMES_CSV_USER_FNAME_FORMAT
    variables.  If the value of either of these are None, they are defaulted
    to '{fname}' and '{lname}', respectively.

    The values for the first_name and last_name elements are obtained by
    taking the variables above and processing with the standard Python
    format() method, which is passed the parameters:
        fname: Set to the value of the User's first_name field
        lname: Set to the value of the User's last_name field
        username: Set to the value of the User's username field
        email: Set to the value of the USer's email field
    """
    if XDMOD_NAMES_CSV_USER_FNAME_FORMAT is None:
        fname_format = '{fname}'
    else:
        fname_format = XDMOD_NAMES_CSV_USER_FNAME_FORMAT
    if XDMOD_NAMES_CSV_USER_LNAME_FORMAT is None:
        lname_format = '{lname}'
    else:
        lname_format = XDMOD_NAMES_CSV_USER_LNAME_FORMAT

    user_list = []

    users = User.objects.all().order_by('username')
    for user in users:
        uname = user.username
        email = user.email
        fname = user.first_name
        lname = user.last_name
        if uname:
            fname_val = fname_format.format(
                    username=uname,
                    fname=fname,
                    lname=lname,
                    email=email,
                    )
            lname_val = lname_format.format(
                    username=uname,
                    fname=fname,
                    lname=lname,
                    email=email,
                    )
            user_list.append( (uname, fname_val, lname_val) )
    return user_list
