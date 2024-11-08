from django.conf import settings
from django.db.models import Q
from coldfront.core.project.models import Project
from coldfront.core.utils.common import import_from_settings
from coldfront.plugins.sftocf.client import StarFishServer
from coldfront.core.utils.local_utils import uniques_and_intersection
from coldfront.plugins.sftocf.utils import get_corresponding_coldfront_resources
from starfish_api_client import StarfishAPIClient

import logging

STARFISH_SERVER = import_from_settings('SF_SERVER', 'starfish')
STARFISH_USER = import_from_settings('SF_USER')
STARFISH_PASSWORD = import_from_settings('SF_PASSWORD')

logger = logging.getLogger(__name__)


def get_project_paths(project_obj):
    """Create a zone from a project object"""
    paths = [
        f"{a.resources.first().name.split('/')[0]}:{a.path}"
        for a in project_obj.allocation_set.filter(
            status__name__in=['Active', 'New', 'Updated', 'Ready for Review'],
            resources__in=get_corresponding_coldfront_resources()
        )
        if a.path
    ]
    
    return paths

def zone_report():
    """Check of SF zone alignment with pipeline specs.
    Report on:
        Coldfront projects with storage allocations vs. SF zones
        AD groups corresponding to SF zones that don't belong to AD group starfish_groups
        SF zones have all allocations that correspond to Coldfront project allocations
        SF zones that don’t have groups
        SF zones that have users as opposed to groups
    """
    report = {
        'projects_with_allocations_no_zones': [],
        'zones_with_no_projects': [],
        'zones_with_no_groups': [],
        'zones_with_users': [],
    }
    # start by getting all zones
    server = StarfishAPIClient(STARFISH_SERVER, STARFISH_USER, STARFISH_PASSWORD)
    # get list of all zones in server
    zones = server.get_zones()

    # get all projects with at least one storage allocation
    projects = Project.objects.filter(
        allocation__status__name__in=['Active'],
        allocation__resources__in=get_corresponding_coldfront_resources(),
    ).distinct()
    # check which of these projects have zones
    project_titles = [p.title for p in projects]
    zone_names = [z['name'] for z in zones]
    projs_no_zones, projs_with_zones, zones_no_projs = uniques_and_intersection(project_titles, zone_names)
    report['projs_with_zones'] = {p['name']:p['id'] for p in [z for z in zones if z['name'] in projs_with_zones]}
    report['projects_with_allocations_no_zones'] = projs_no_zones
    report['zones_with_no_projects'] = zones_no_projs
    no_group_zones = [z['name'] for z in zones if not z['managing_groups']]
    report['zones_with_no_groups'] = no_group_zones
    user_zones = [z for z in zones if z['managers']]
    report['zones_with_users'] = [
        f"{z['name']}: {z['managers']}" for z in user_zones
    ]
    report_nums = {k: len(v) for k, v in report.items()}
    for r in [report, report_nums]:
        print(r)
        logger.warning(r)


def allocation_to_zone(allocation):
    """
    1. Check whether the allocation is in Starfish
    2. If so, check whether a zone exists for the allocation's project.
    3. If not, create a zone for the allocation's project.
    4. Add the allocation to the zone.
    """
    server = StarfishAPIClient(STARFISH_SERVER, STARFISH_USER, STARFISH_PASSWORD)

    resource = allocation.resources.first()
    if not any(sf_res in resource.title for sf_res in server.volumes):
        return None
    project = allocation.project
    zone = server.get_zone_by_name(project.title)
    if zone:
        zone_paths = zone['paths']
        new_path = f"{allocation.resources.first().name.split('/')[0]}:{allocation.path}"
        zone_paths.append(new_path)
        for group in zone['managing_groups']:
            add_zone_group_to_ad(group['groupname'])
        zone.update_zone(paths=zone_paths)
    else:
        paths = get_project_paths(project)
        add_zone_group_to_ad(project.title)
        zone = server.create_zone(project.title, paths, [], [{'groupname': project.title}])
    return zone


def add_zone_group_to_ad(group_name):
    """Add a zone group to the AD group starfish_groups"""
    if 'coldfront.plugins.ldap' in settings.INSTALLED_APPS:
        from coldfront.plugins.ldap.utils import LDAPConn
        ldap_conn = LDAPConn()
        try:
            ldap_conn.add_group_to_group(group_name, 'starfish_users')
        except Exception as e:
            # no exception if group is already present
            # exception if group doesn't exist
            error = f'Error adding {group_name} to starfish_users: {e}'
            print(error)
            logger.warning(error)
            raise
    else:
        error = 'LDAP not installed, cannot add group to starfish_users'
        print(error)
        logger.warning(error)
        raise ImportError(error)