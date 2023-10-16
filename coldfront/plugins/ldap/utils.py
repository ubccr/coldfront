"""
utility functions for LDAP interaction
"""
import logging
import operator
from functools import reduce

from django.db.models import Q
from django.utils import timezone
from django.contrib.auth import get_user_model
from ldap3 import Connection, Server, ALL_ATTRIBUTES
from ldap3.extend.microsoft.addMembersToGroups import ad_add_members_to_groups
from ldap3.extend.microsoft.removeMembersFromGroups import ad_remove_members_from_groups

from coldfront.core.utils.common import import_from_settings
from coldfront.core.field_of_science.models import FieldOfScience
from coldfront.core.utils.fasrc import (
    id_present_missing_users,
    log_missing,
    slate_for_check,
    sort_by,
)
from coldfront.core.project.models import (
    Project,
    ProjectStatusChoice,
    ProjectUserRoleChoice,
    ProjectUserStatusChoice,
    ProjectUser,
)

logger = logging.getLogger(__name__)


class LDAPConn:
    """
    LDAP connection object
    """
    def __init__(self, test=False):

        AUTH_LDAP_SERVER_URI = (
            'TEST_AUTH_LDAP_SERVER_URI' if test else 'AUTH_LDAP_SERVER_URI')
        AUTH_LDAP_BIND_DN = (
            'TEST_AUTH_LDAP_BIND_DN' if test else 'AUTH_LDAP_BIND_DN')
        AUTH_LDAP_BIND_PASSWORD = (
            'TEST_AUTH_LDAP_BIND_PASSWORD' if test else 'AUTH_LDAP_BIND_PASSWORD')
        AUTH_LDAP_USER_SEARCH_BASE = (
            'TEST_AUTH_LDAP_USER_SEARCH_BASE' if test else 'AUTH_LDAP_USER_SEARCH_BASE')
        AUTH_LDAP_GROUP_SEARCH_BASE = (
            'TEST_AUTH_LDAP_GROUP_SEARCH_BASE' if test else 'AUTH_LDAP_GROUP_SEARCH_BASE')
        LDAP_CONNECT_TIMEOUT = (
            'TEST_LDAP_CONNECT_TIMEOUT' if test else 'LDAP_CONNECT_TIMEOUT')
        AUTH_LDAP_USE_SSL = (
            'TEST_AUTH_LDAP_USE_SSL' if test else 'AUTH_LDAP_USE_SSL')

        self.LDAP_SERVER_URI = import_from_settings(AUTH_LDAP_SERVER_URI, None)
        self.LDAP_BIND_DN = import_from_settings(AUTH_LDAP_BIND_DN, None)
        self.LDAP_BIND_PASSWORD = import_from_settings(AUTH_LDAP_BIND_PASSWORD, None)
        self.LDAP_USER_SEARCH_BASE = import_from_settings(AUTH_LDAP_USER_SEARCH_BASE, None)
        self.LDAP_GROUP_SEARCH_BASE = import_from_settings(AUTH_LDAP_GROUP_SEARCH_BASE, None)
        self.LDAP_CONNECT_TIMEOUT = import_from_settings(LDAP_CONNECT_TIMEOUT, 20)
        self.LDAP_USE_SSL = import_from_settings(AUTH_LDAP_USE_SSL, False)
        self.server = Server(self.LDAP_SERVER_URI, use_ssl=self.LDAP_USE_SSL, connect_timeout=self.LDAP_CONNECT_TIMEOUT)
        self.conn = Connection(self.server, self.LDAP_BIND_DN, self.LDAP_BIND_PASSWORD, auto_bind=True)

    def search(self, attr_search_dict, search_base, attributes=ALL_ATTRIBUTES):
        """Run an LDAP search.

        Parameters
        ----------
        attr_search_dict : dict
            keys are attribute names, values are the values to search for.
            Values can include asterisks for wildcard searches.
            example: {'cn': 'Bob Smith', 'company': 'FAS'}
        search_base : string
            should appear similar to 'ou=Domain Users,dc=mydc,dc=domain'
        attributes : list or ALL_ATTRIBUTES object
            attributes to return or ldap search objects (e.g., ALL_ATTRIBUTES)
        """
        search_filter = format_template_assertions(attr_search_dict)
        search_parameters = {
            'search_base': search_base,
            'search_filter': search_filter,
            'attributes': attributes,
        }
        self.conn.search(**search_parameters)
        return self.conn.entries

    def search_users(self, attr_search_dict, attributes=ALL_ATTRIBUTES, return_as='dict'):
        """search for users.
        Parameters
        ----------
        attr_search_dict : dict
            keys are attribute names, values are the values to search for.
            Values can include asterisks for wildcard searches.
            example: {'cn': 'Bob Smith', 'company': 'FAS'}
        attributes : list or ALL_ATTRIBUTES object
            attributes to return or ldap search objects (e.g., ALL_ATTRIBUTES)
        return_as : string
            if 'dict', return entry_attributes_as_dict. Otherwise, return ldap3 entries.
        """
        user_entries = self.search(
            attr_search_dict, self.LDAP_USER_SEARCH_BASE, attributes=attributes
        )
        if return_as == 'dict':
            user_entries = [e.entry_attributes_as_dict for e in user_entries]
        return user_entries

    def search_groups(self, attr_search_dict, attributes=ALL_ATTRIBUTES, return_as='dict'):
        """search for groups.
        Parameters
        ----------
        attr_search_dict : dict
            keys are attribute names, values are the values to search for.
            Values can include asterisks for wildcard searches.
            example: {'cn': 'Bob Smith', 'company': 'FAS'}
        attributes : list or ALL_ATTRIBUTES object
            attributes to return or ldap search objects (e.g., ALL_ATTRIBUTES)
        return_as : string
            if 'dict', return entry_attributes_as_dict. Otherwise, return ldap3 entries.
        """
        group_entries = self.search(
            attr_search_dict, self.LDAP_GROUP_SEARCH_BASE, attributes=attributes
        )
        if return_as == 'dict':
            group_entries = [e.entry_attributes_as_dict for e in group_entries]
        return group_entries

    def return_multi_group_members_manager(self, samaccountname_list):
        """return tuples of user and PI entries for each group listed in samaccountname_list
        """
        group_entries = self.search_groups(
            {'sAMAccountName': samaccountname_list},
            attributes=['managedBy', 'distinguishedName', 'sAMAccountName', 'member']
        )
        manager_members_tuples = []
        for entry in group_entries:
            manager_members_tuples.append(self.manager_members_from_group(entry))
        return manager_members_tuples

    def return_user_by_name(self, username, return_as='dict', attributes=ALL_ATTRIBUTES):
        """Return an AD user entry by the username"""
        user = self.search_users({"uid": username}, return_as=return_as, attributes=attributes)
        if len(user) > 1:
            raise ValueError("too many users in value returned")
        if not user:
            raise ValueError("no users returned")
        return user[0]

    def return_group_by_name(self, groupname, return_as='dict'):
        group = self.search_groups({"sAMAccountName": groupname}, return_as=return_as)
        if len(group) > 1:
            raise ValueError("too many groups in value returned")
        if not group:
            raise ValueError("no groups returned")
        return group[0]

    def add_member_to_group(self, user_name, group_name):
        # get group
        group = self.return_group_by_name(group_name)
        # get user
        try:
            user = self.return_user_by_name(user_name)
        except ValueError as e:
            raise e
        group_dn = group['distinguishedName']
        user_dn = user['distinguishedName']
        try:
            result = ad_add_members_to_groups(self.conn, [user_dn], group_dn, fix=True)
        except Exception as e:
            raise e
        return result

    def remove_member_from_group(self, user_name, group_name):
        # get group
        try:
            group = self.return_group_by_name(group_name)
        except ValueError as e:
            raise e
        # get user
        try:
            user = self.return_user_by_name(user_name)
        except ValueError as e:
            raise e
        if user['gidNumber'] == group['gidNumber']:
            raise ValueError("group is user's primary group - please contact FASRC support to remove this user from your group.")
        group_dn = group['distinguishedName']
        user_dn = user['distinguishedName']
        try:
            result = ad_remove_members_from_groups(self.conn, [user_dn], group_dn, fix=True)
        except Exception as e:
            raise e
        return result

    def determine_primary_group_membership(self, usernames, groupname):
        """Return two lists of users based on membership in the specified group.
        """
        group = self.return_group_by_name(groupname)
        attrs = ['sAMAccountName', 'gidNumber']
        users = [self.return_user_by_name(user, attributes=attrs) for user in usernames]
        in_group = lambda u: u['gidNumber'] == group['gidNumber']
        users_in_group = sort_by(users, in_group, how='condition')
        return users_in_group

    def return_group_members_manager(self, samaccountname):
        """return user entries that are members of the specified group.

        Parameters
        ----------
        samaccountname : string
            sAMAccountName of the group to search for
        """
        logger.debug('return_group_members_manager for Project %s', samaccountname)
        group_entries = self.search_groups(
            {'sAMAccountName': samaccountname},
            attributes=['managedBy', 'distinguishedName','sAMAccountName', 'member']
        )
        if len(group_entries) > 1:
            return 'multiple groups with same sAMAccountName'
        if not group_entries:
            return 'no matching groups found'
        group_entry = group_entries[0]
        return self.manager_members_from_group(group_entry)

    def manager_members_from_group(self, group_entry):
        group_dn = group_entry['distinguishedName'][0]
        user_attr_list = [
            'sAMAccountName', 'cn', 'name', 'title', 'department',
            'distinguishedName', 'accountExpires', 'info', 'userAccountControl'
        ]
        group_members = self.search_users({'memberOf': group_dn}, attributes=user_attr_list)
        logger.debug('group_members:\n%s', group_members)
        try:
            group_manager_dn = group_entry['managedBy'][0]
        except Exception as e:
            return 'no manager specified'
        manager_attr_list = user_attr_list + ['memberOf']
        group_manager = self.search_users(
            {'distinguishedName': group_manager_dn}, attributes=manager_attr_list
        )
        logger.debug('group_manager:\n%s', group_manager)
        if not group_manager:
            return 'no ADUser manager found'
        return (group_members, group_manager[0])


def user_valid(user):
    return user['userAccountControl'][0] in [512, 66048]
    # and (user['accountExpires'][0].year == 1601 or user['accountExpires'][0] > timezone.now())

class GroupUserCollection:
    """
    Class to hold a group and its members.
    """
    def __init__(self, group_name, ad_users, pi, project=None):
        self.name = group_name
        self.members = ad_users
        self.pi = pi
        self.project = project

    @property
    def current_ad_users(self):
        return [u for u in self.members if user_valid(u)]

    @property
    def pi_is_active(self):
        """Return true if PI's account is both unexpired and not disabled."""
        return user_valid(self.pi)

    def compare_active_members_projectusers(self):
        """Compare ADGroup members to ProjectUsers.

        Returns
        -------
        members_only : list
            users present in the members list and not as Coldfront ProjectUsers.
        projuser_only : list
            Coldfront ProjectUsers missing from the members list.
        """
        ### check presence of ADGroup members in Coldfront  ###
        logger.debug('membership data collected for %s\nraw ADUser data for %s users',
        self.name, len(self.members))
        if self.current_ad_users:
            logger.debug('(%s of %s users valid)', len(self.current_ad_users), len(self.members))
            ad_users = [u['sAMAccountName'][0] for u in self.current_ad_users]
        else:
            logger.warning('WARNING: NO AD USERS RETURNED FOR %s', self.project.title)
            ad_users = []
        proj_usernames = [
            pu.user.username for pu in self.project.projectuser_set.filter(
                    (~Q(status__name='Removed')))
        ]
        logger.debug('projectusernames: %s', proj_usernames)

        members_only, _, projuser_only = uniques_and_intersection(ad_users, proj_usernames)
        return (members_only, projuser_only)


def format_template_assertions(attr_search_dict, search_operator='and'):
    """Format attr_search_string_dict into correct filter_template
    Parameters
    ----------
    attr_search_dict : dict
        keys are attribute names, values are the values to search for.
        Values can include asterisks for wildcard searches.
        Values can also be lists of values to search for.
        example: {'cn': 'Bob*', 'company': ['FAS', 'HKS']}
    search_operator : str
        options are 'and' or 'or'

    Returns
    -------
    output should be string formatted like '(|(cn=Bob Smith)(company=FAS))'
    """

    match_operator = {'and':'&', 'or':'|'}
    val_string = lambda k, v: f'({k}={v})' if is_string(v) else '(|'+ ''.join(f'({k}={i})' for i in v) + ')'
    filter_template_vars = [val_string(k, v) for k, v in attr_search_dict.items()]
    search_filter = ''.join(filter_template_vars)
    if len(filter_template_vars) > 1:
        search_filter = f'({match_operator[search_operator]}'+search_filter+')'
    return search_filter

def uniques_and_intersection(list1, list2):
    intersection = list(set(list1) & set(list2))
    list1_unique = list(set(list1) - set(list2))
    list2_unique = list(set(list2) - set(list1))
    return (list1_unique, intersection, list2_unique)


def is_string(value):
    return isinstance(value, str)

def sort_dict_on_conditional(dict1, condition):
    """split one dictionary into two on basis of value's ability to meet a condition
    """
    is_true, is_false = {}, {}
    for k, v in dict1.items():
        (is_false, is_true)[condition(v)][k] = v
    return is_true, is_false

def cleaned_membership_query(proj_membs_mans):
    search_errors, proj_membs_mans = sort_dict_on_conditional(proj_membs_mans, is_string)
    if search_errors:
        logger.error('could not return members and manager for some groups:\n%s',
                        search_errors)
    return proj_membs_mans, search_errors

def remove_inactive_disabled_managers(groupusercollections):
    """Remove groupusercollections with inactive managers"""
    active_pi_groups, inactive_pi_groups = sort_by(groupusercollections, 'pi_is_active', how='attr')
    if inactive_pi_groups:
        logger.error('LDAP query returns Active Projects with expired PIs: %s',
        {group.name: group.pi['sAMAccountName'][0] for group in inactive_pi_groups})
    return active_pi_groups, inactive_pi_groups

def flatten(l):
    return [item for sublist in l for item in sublist]



def collect_update_project_status_membership():
    """
    Update Project and ProjectUser entries for existing Coldfront Projects using
    ADGroup and ADUser data.
    """
    # collect commonly used db objects
    projectuser_role_user = ProjectUserRoleChoice.objects.get(name='User')
    projectuserstatus_active = ProjectUserStatusChoice.objects.get(name='Active')
    projectusers_to_remove = []

    active_projects = Project.objects.filter(
        status__name__in=['Active', 'New']).prefetch_related('projectuser_set')

    ad_conn = LDAPConn()

    proj_membs_mans = {p: ad_conn.return_group_members_manager(p.title) for p in active_projects}
    proj_membs_mans, _ = cleaned_membership_query(proj_membs_mans)
    groupusercollections = [GroupUserCollection(k.title, v[0], v[1], project=k) for k, v in proj_membs_mans.items()]

    active_pi_groups, inactive_pi_groups = remove_inactive_disabled_managers(groupusercollections)
    projects_to_deactivate = [g.project for g in inactive_pi_groups]
    Project.objects.bulk_update([Project(id=p.pk, status=ProjectStatusChoice.objects.get(name='Inactive'))
                                    for p in projects_to_deactivate], ['status'])
    logger.debug('projects_to_deactivate %s', projects_to_deactivate)
    if projects_to_deactivate:
        pis_to_deactivate = ProjectUser.objects.filter(
            reduce(operator.or_, (
                Q(project=p) & Q(user=p.pi) for p in projects_to_deactivate)
            ))
        logger.debug('pis_to_deactivate %s', pis_to_deactivate)
        pis_to_deactivate.update(status=ProjectUserStatusChoice.objects.get(name='Removed'))
        logger.info('deactivated projects and pis: %s', [(pi.project.title, pi.user.username) for pi in pis_to_deactivate])

    ### identify PIs with incorrect roles and change their status ###
    projectuser_role_manager = ProjectUserRoleChoice.objects.get(name='Manager')

    pis_mislabeled = ProjectUser.objects.filter(
        reduce(operator.or_,
            ((  Q(project=group.project) &
                Q(user__username=group.pi['sAMAccountName']) &
                ~Q(role=projectuser_role_manager))
            for group in active_pi_groups)
            )
        )

    if pis_mislabeled:
        logger.info('Project PIs with incorrect labeling: %s',
            [(pi.project.title, pi.user.username) for pi in pis_mislabeled])
        ProjectUser.objects.bulk_update([
            ProjectUser(id=pi.id, role=projectuser_role_manager)
            for pi in pis_mislabeled
        ], ['role'])

    for group in active_pi_groups:

        ad_users_not_added, remove_projuser_names = group.compare_active_members_projectusers()

        # handle any AD users not in Coldfront
        if ad_users_not_added:
            logger.debug(
                'ad_users_not_added - ADUsers not in ProjectUsers:\n%s',
                ad_users_not_added
            )
            # find accompanying ifxusers in the system and add as ProjectUsers
            present_project_ifxusers, missing_users = id_present_missing_users(ad_users_not_added)
            logger.debug(
                'present_project_ifxusers - ADUsers who have ifxuser accounts:\n%s',
                ad_users_not_added
            )

            log_missing('user', missing_users) # log missing IFXusers

            # If user is missing because status was changed to 'removed', update status
            present_projectusers = group.project.projectuser_set.filter(
                user__in=present_project_ifxusers
            )
            logger.debug('present_users - ADUsers who have ifxuser accounts:\n%s', ad_users_not_added)
            if present_projectusers:
                logger.warning('found reactivated ADUsers for project %s: %s',
                    group.project.title, [user.user.username for user in present_projectusers])

                present_projectusers.update(
                    role=projectuser_role_user, status=projectuserstatus_active
                )
            # create new entries for all new ProjectUsers
            missing_projectusers = present_project_ifxusers.exclude(
                id__in=[pu.user.pk for pu in present_projectusers]
            )
            logger.debug("missing_projectusers - ifxusers in present_project_ifxusers who are not ")
            ProjectUser.objects.bulk_create([ProjectUser(
                                                project=group.project,
                                                user=user,
                                                role=projectuser_role_user,
                                                status=projectuserstatus_active
                                            )
                                            for user in missing_projectusers
                                ])

        ### identify inactive ProjectUsers, slate for status change ###
        remove_projusers = group.project.projectuser_set.filter(
                        user__username__in=remove_projuser_names)
        logger.debug("remove_projusers - projectusers slated for removal:\n %s", remove_projusers)
        projectusers_to_remove.extend(list(remove_projusers))

    ### update status of projectUsers slated for removal ###
    # change ProjectUser status to Removed
    projectuserstatus_removed = ProjectUserStatusChoice.objects.get(name='Removed')
    ProjectUser.objects.bulk_update([
        ProjectUser(id=pu.id, status=projectuserstatus_removed)
        for pu in projectusers_to_remove
    ], ['status'])
    logger.info('changing status of these ProjectUsers to "Removed":%s',
            [(pu.user.username, pu.project.title) for pu in projectusers_to_remove])

def import_projects_projectusers(projects_list):
    """Use AD user and group information to automatically create new
    Coldfront Projects from projects_list.
    """
    errortracker = {
        'no_pi': [],
        'not_found': [],
        'no_fos': [],
        'pi_not_projectuser': [],
        'pi_active_invalid': []
    }
    # if project already exists, end here
    existing_projects = Project.objects.filter(title__in=projects_list)
    if existing_projects:
        logger.debug('existing projects: %s', [p.title for p in existing_projects])
    projects_to_add = [p for p in projects_list if p not in [p.title for p in existing_projects]]

    ad_conn = LDAPConn()
    proj_membs_mans = {proj: ad_conn.return_group_members_manager(proj) for proj in projects_to_add}
    proj_membs_mans, search_errors = cleaned_membership_query(proj_membs_mans)
    errortracker['not_found'] = search_errors
    groupusercollections = [
        GroupUserCollection(k, v[0], v[1]) for k, v in proj_membs_mans.items()
    ]

    added_projects, errortracker = add_new_projects(groupusercollections, errortracker)
    return added_projects, errortracker


def add_new_projects(groupusercollections, errortracker):
    """create new Coldfront Projects and ProjectUsers from PI and AD user data
    already collected from ATT.
    """
    # if PI is inactive, don't add project
    active_pi_groups, _ = remove_inactive_disabled_managers(groupusercollections)
    logger.debug('active_pi_groups: %s', active_pi_groups)
    # if PI lacks 'harvard_faculty' or 'non_faculty_pi' Affiliation, don't add
    pi_groups = ['harvard_faculty', 'non_faculty_pi']
    active_valid_pi_groups = [
        g for g in active_pi_groups
        if any(any(string in m for string in pi_groups) for m in g.pi['memberOf'])
    ]
    logger.debug('active_invalid_pi_groups: %s', set(active_valid_pi_groups) - set(active_pi_groups))

    errortracker['pi_active_invalid'] = [group.name for group in active_pi_groups
        if group not in active_valid_pi_groups]
    # identify all users not in ifx
    user_entries = flatten([g.members + [g.pi] for g in active_valid_pi_groups])
    user_names = {u['sAMAccountName'][0] for u in user_entries}
    _, missing_users = id_present_missing_users(user_names)
    missing_usernames = {d['username'] for d in missing_users}

    active_present_pi_groups = [
        g for g in active_valid_pi_groups if g.pi['sAMAccountName'][0] not in missing_usernames
    ]
    missing_pi_groups = [g for g in groupusercollections if g not in active_present_pi_groups]
    missing_pis = [
        {'username': g.pi['sAMAccountName'][0], 'group': g.name} for g in missing_pi_groups
    ]
    log_missing('user', missing_pis)
    # record and remove projects where pis aren't available
    errortracker['no_pi'] = [
        g.name for g in groupusercollections if g not in active_present_pi_groups
    ]

    added_projects = []
    for group in active_present_pi_groups:
        logger.debug('source: %s\n%s\n%s', group.name, group.members, group.pi)
        # collect group membership entries
        member_usernames = {u['sAMAccountName'][0] for u in group.current_ad_users} - missing_usernames
        missing_members = [
            {'username': m['sAMAccountName'][0], 'group': group.name} for m in group.members
        ]
        log_missing('user', missing_members)

        # locate field_of_science
        if 'department' in group.pi.keys() and group.pi['department']:
            field_of_science_name=group.pi['department'][0]
            logger.debug('field_of_science_name %s', field_of_science_name)
            field_of_science_obj, created = FieldOfScience.objects.get_or_create(
                description=field_of_science_name, defaults={'is_selectable':'True'}
            )
            if created:
                logger.info('added new field_of_science: %s', field_of_science_name)
        else:
            errortracker['no_fos'].append(group.name)
            message = f'no department for AD group {group.name}, will not add unless fixed'
            logger.warning(message)
            print(f'HALTING: {message}')
            issue = {
                'error': message,
                'program': 'ldap.utils.add_new_projects',
                'url': 'NA; AD issue',
            }
            slate_for_check([issue])
            print(group.pi)
            continue

        ### CREATE PROJECT ###
        project_pi = get_user_model().objects.get(username=group.pi['sAMAccountName'][0])
        description = f'Allocations for {group.name}'

        group.project = Project.objects.create(
            created=timezone.now(),
            modified=timezone.now(),
            title=group.name,
            pi=project_pi,
            description=description.strip(),
            field_of_science=field_of_science_obj,
            requires_review=False,
            status=ProjectStatusChoice.objects.get(name='New')
        )

        ### add projectusers ###
        users_to_add = get_user_model().objects.filter(username__in=member_usernames)
        added_projectusers = ProjectUser.objects.bulk_create([
                ProjectUser(
                    project=group.project,
                    user=user,
                    status=ProjectUserStatusChoice.objects.get(name='Active'),
                    role=ProjectUserRoleChoice.objects.get(name='User'),
                )
                for user in users_to_add
        ])
        logger.debug('added projectusers: %s', added_projectusers)
        # add permissions to PI/manager-status ProjectUsers
        logger.debug('adding manager status to ProjectUser %s for Project %s',
                    group.pi['sAMAccountName'][0], group.name)
        try:
            manager = group.project.projectuser_set.get(user__username=group.pi['sAMAccountName'][0])
        except ProjectUser.DoesNotExist:
            logger.warning('PI %s not found in ProjectUser for Project %s',
                        group.pi['sAMAccountName'][0], group.name)
            errortracker['pi_not_projectuser'].append(group.name)
            continue
        manager.role = ProjectUserRoleChoice.objects.get(name='Manager')
        manager.save()
        added_projects.append([group.name, group.project])

    for errortype in errortracker:
        logger.warning('AD groups with %s: %s', errortype, errortracker[errortype])
    return added_projects, errortracker
