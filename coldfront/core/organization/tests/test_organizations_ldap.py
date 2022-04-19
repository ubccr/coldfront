# Script to test Directory2Organization and LDAP integration methods

import sys

from django.core.exceptions import ValidationError 
from django.db.models import ProtectedError
from django.test import TestCase

from coldfront.core.utils.libtest import ConfigChangingTestCase
from coldfront.core.organization.signals import populate_user_organizations

from django.contrib.auth.models import User
from coldfront.core.project.models import Project
from coldfront.core.organization.models import (
        Organization,
        OrganizationUser,
        OrganizationProject,
        Directory2Organization,
        )

VERBOSE_TESTS = set()
#VERBOSE_TESTS.add('populate')
#VERBOSE_TESTS.add('set_user')
#VERBOSE_TESTS.add('set_proj')

LDAPSTR_ENAE = 'ENGR-Aerospace Engineering'
LDAPSTR_PHYS = 'CMNS-Physics'
LDAPSTR_PHYS2 = 'CMNS-Physics-Joint Quantum Institute'
LDAPSTR_PHYS3 = 'CMNS-Physics-Quantum Materials Center'
LDAPSTR_ASTR= 'CMNS-Astronomy'

LDAPSTR_UNKNOWN_PLACEHOLDER='NEWUNKNOWNORG'

WILBUR_ENAE_PRIMARY = {
            'user': 'wilbur',
            'organization': 'UMD-ENGR-ENAE',
            'is_primary': True,
        }

WILBUR_ENAE_SECONDARY = {
            'user': 'wilbur',
            'organization': 'UMD-ENGR-ENAE',
            'is_primary': False
        }

WILBUR_PHYS_PRIMARY = {
            'user': 'wilbur',
            'organization': 'UMD-CMNS-PHYS',
            'is_primary': True,
        }

WILBUR_PHYS_SECONDARY = {
            'user': 'wilbur',
            'organization': 'UMD-CMNS-PHYS',
            'is_primary': False
        }

WILBUR_ASTR_PRIMARY = {
            'user': 'wilbur',
            'organization': 'UMD-CMNS-ASTR',
            'is_primary': True,
        }

WILBUR_ASTR_SECONDARY = {
            'user': 'wilbur',
            'organization': 'UMD-CMNS-ASTR',
            'is_primary': False
        }

WILBUR_UNKNOWN_PRIMARY = {
            'user': 'wilbur',
            'organization': LDAPSTR_UNKNOWN_PLACEHOLDER,
            'is_primary': True,
        }

WILBUR_UNKNOWN_SECONDARY = {
            'user': 'wilbur',
            'organization': LDAPSTR_UNKNOWN_PLACEHOLDER,
            'is_primary': False,
        }

WILBUR_ORGS_INITIAL = [
        WILBUR_ENAE_PRIMARY,
        WILBUR_PHYS_SECONDARY,
    ]

WILBUR_ORGS_SWAP_PRIMARY = [
        WILBUR_PHYS_PRIMARY,
        WILBUR_ENAE_SECONDARY,
    ]

WILBUR_ORGS_PLUS_ASTR = [
        WILBUR_ENAE_PRIMARY,
        WILBUR_ASTR_SECONDARY,
        WILBUR_PHYS_SECONDARY,
    ]

FLIGHT_PROJ = 'Hyposonic Flight'

FLIGHT_ENAE_PRIMARY = {
            'project': FLIGHT_PROJ,
            'organization': 'UMD-ENGR-ENAE',
            'is_primary': True,
        }

FLIGHT_ENAE_SECONDARY = {
            'project': FLIGHT_PROJ,
            'organization': 'UMD-ENGR-ENAE',
            'is_primary': False
        }

FLIGHT_PHYS_PRIMARY = {
            'project': FLIGHT_PROJ,
            'organization': 'UMD-CMNS-PHYS',
            'is_primary': True,
        }

FLIGHT_PHYS_SECONDARY = {
            'project': FLIGHT_PROJ,
            'organization': 'UMD-CMNS-PHYS',
            'is_primary': False
        }

FLIGHT_ASTR_PRIMARY = {
            'project': FLIGHT_PROJ,
            'organization': 'UMD-CMNS-ASTR',
            'is_primary': True,
        }

FLIGHT_ASTR_SECONDARY = {
            'project': FLIGHT_PROJ,
            'organization': 'UMD-CMNS-ASTR',
            'is_primary': False
        }

FLIGHT_ORGS_INITIAL = [
        FLIGHT_ENAE_PRIMARY,
        FLIGHT_PHYS_SECONDARY,
    ]

FLIGHT_ORGS_SWAP_PRIMARY = [
        FLIGHT_PHYS_PRIMARY,
        FLIGHT_ENAE_SECONDARY,
    ]

FLIGHT_ORGS_PLUS_ASTR = [
        FLIGHT_ENAE_PRIMARY,
        FLIGHT_ASTR_SECONDARY,
        FLIGHT_PHYS_SECONDARY,
    ]

class OrganizationLDAPTest(ConfigChangingTestCase):
    fixtures = ['organization_test_data.json']

    # Fake _LDAPUser class
    class FakeLDAPUser:
        """This is a Fake version of django_auth_ldap.backend._LDAPUser.

        We just mimic a couple of public functions, enough for our tests
        to work.
        """
        def __init__(self, 
                attrs={}, 
                dn='test', 
                group_dns=set(), 
                group_names=set(),
            ):
            self.attrs = attrs
            self.dn = dn
            self.group_dns = group_dns
            self.group_names = group_names
        #end: def FakeLDAPUser.__init__
    #end: class FakeLDAPUser

    # Helper functions
    def orguser_to_dict(self, orguser):
        """Convert an OrganizationUser to a dict"""
        retval = {
                'user': orguser.user.user.username,
                'organization': orguser.organization.fullcode(),
                'is_primary': orguser.is_primary,
           }
        return retval

    def orgusers_to_dicts(self, orgusers):
        """Run orguser_to_dict on a list of orgusers"""
        retval = []
        for orguser in orgusers:
            tmp = self.orguser_to_dict(orguser)
            retval.append(tmp)
        return retval

    def dump_orguser(self, orguser):
        """For debugging: dumps an OrganizationUser instance to stderr"""
        uname = orguser.user.user.username
        org = orguser.organization.fullcode()
        isprimary = orguser.is_primary
        sys.stderr.write('[DEBUG] OrgUser={}:{} [primary={}]\n'.format(
            uname, org, isprimary))
        return

    def dump_orgusers(self, orgusers):
        """For debugging: dumps a list of  OrganizationUsers to stderr"""
        for orguser in orgusers:
            self.dump_orguser(orguser)
        return

    def orgproj_to_dict(self, orgproj):
        """Convert an OrganizationProject to a dict"""
        retval = {
                'project': orgproj.project.title,
                'organization': orgproj.organization.fullcode(),
                'is_primary': orgproj.is_primary,
           }
        return retval

    def orgprojs_to_dicts(self, orgprojs):
        """Run orgproj_to_dict on a list of orgprojs"""
        retval = []
        for orgproj in orgprojs:
            tmp = self.orgproj_to_dict(orgproj)
            retval.append(tmp)
        return retval

    def dump_orgproj(self, orgproj):
        """For debugging: dumps an OrganizationProject instance to stderr"""
        pname = orgproj.project.title
        org = orgproj.organization.fullcode()
        isprimary = orgproj.is_primary
        sys.stderr.write('[DEBUG] OrgProj={}:{} [primary={}]\n'.format(
            org, pname,  isprimary))
        return

    def dump_orgprojs(self, orgprojs):
        """For debugging: dumps a list of  OrganizationProjs to stderr"""
        for orgproj in orgprojs:
            self.dump_orgproj(orgproj)
        return

    def do_set_organizations_for_user_test(self, username, orglist, expected,
            delete=False, default_first_primary=False, testname='unknown test'):
        """Run test of set_organizations_for_user
        """
        user = User.objects.get(username=username)
        uprof = user.userprofile

        OrganizationUser.set_organizations_for_user(
                    user=user,
                    organization_list=orglist,
                    delete=delete,
                    default_first_primary=default_first_primary,
            )

        # Get results
        qset = OrganizationUser.objects.filter(user=uprof)
        got = self.orgusers_to_dicts(qset)

        if 'set_user' in VERBOSE_TESTS:
            sys.stderr.write('[DEBUG] Test {} got\n'.format(testname))
            self.dump_orgusers(qset)
            sys.stderr.write('\n')

        self.assertEqual(got, expected, testname)

        return

    def do_set_organizations_for_proj_test(self, project, orglist, expected,
            delete=False, default_first_primary=False, testname='unknown test'):
        """Run test of set_organizations_for_project
        """
        proj = Project.objects.get(title=project)

        OrganizationProject.set_organizations_for_project(
                    project=proj,
                    organization_list=orglist,
                    delete=delete,
                    default_first_primary=default_first_primary,
            )

        # Get results
        qset = OrganizationProject.objects.filter(project=proj)
        got = self.orgprojs_to_dicts(qset)

        if 'set_proj' in VERBOSE_TESTS:
            sys.stderr.write('[DEBUG] Test {} got\n'.format(testname))
            self.dump_orgprojs(qset)
            sys.stderr.write('\n')

        self.assertEqual(got, expected, testname)

        return

    def do_populate_user_test(self, varhash, username, attribs, 
            expected, testname='unknown', expect_new_unknown=False):
        """Run a test that fakes a call to populate_user_organizations.

        Like would happen when user logs in with auth_ldap and
        ORGANIZATION_LDAP_AUTH_POPULATE_USER_ORGANIZATIONS set.
        """
        self.set_and_cache_coldfront_config_variables(varhash)
        user = User.objects.get(username=username)
        uprof = user.userprofile

        #First, ensure Unknown root org exists
        unknown_root = Organization.objects.get(code='Unknown', parent=None)
        if not unknown_root:
            self.fail('{}: Unable to find root level "Unknown" Organization'.format(
                testname))
        #And that it has no children
        old_unknown_children = set()
        qset = Organization.objects.filter(parent=unknown_root)
        if qset:
            for tmp in qset:
                old_unknown_children.add(tmp)
            unknown_children = [x.fullcode() for x in qset]
            self.fail('{}: Unknown root org {} has children [{}]'.format(
                testname,
                unknown_root.fullcode(), 
                ', '.join(unknown_children) 
                ) )

        # Fake call to auth_ldap populate user handler
        sender = None
        ldap_user = self.FakeLDAPUser(
                dn='uid={},ou=people,dc=example,dc=com'.format(username),
                attrs=attribs,
            )
        populate_user_organizations(
                sender=sender, 
                user=user,
                ldap_user=ldap_user,
            )

        # Get results
        qset = OrganizationUser.objects.filter(user=uprof)
        got = self.orgusers_to_dicts(qset)

        #Check for a new unknown Org under unknown_root
        qset2 = Organization.objects.filter(parent=unknown_root)
        new_unknown_child = None
        if qset2:
            new_unknown_children = []
            for tmp in qset2:
                if tmp not in old_unknown_children:
                    new_unknown_children.append(tmp)
            #end: for tmp
            numnew = len(new_unknown_children)
            if numnew > 1:
                tmp = [ x.fullcode for x in new_unknown_children ]
                self.fail('Multiple newly created suborgs of {}: [{}]'.format(
                    unknown_root.fullcode(), ', '.join(tmp) ))
            elif numnew:
                new_unknown_child = new_unknown_children[0]
            #end: if numnuew > 1
        #end: if qset2

        if expect_new_unknown:
            # We are expecting an new Unknown org to have been created
            if new_unknown_child is None:
                self.fail('Expecting a new Unknown suborg of {}, but none '
                        'found.'.format(unknown_root.fullcode()))
            oldexpected = expected
            expected = []
            unknown_fcode = new_unknown_child.fullcode()
            for erec in oldexpected:
                new = erec
                if isinstance(erec, str):
                    if erec == LDAPSTR_UNKNOWN_PLACEHOLDER:
                        new = unknown_fcode
                elif isinstance(erec, dict):
                    if 'organization' in erec:
                        if erec['organization'] == LDAPSTR_UNKNOWN_PLACEHOLDER:
                            new = dict(erec) #Make a shallow copy
                            new['organization'] = unknown_fcode
                        #end: if erec['org']
                    #end: if 'organization' in erec
                #end: if isinstance
                expected.append(new)
            #end: for erec
        #end: if expect_new_unknown

        if 'populate' in VERBOSE_TESTS:
            sys.stderr.write('[DEBUG] Test {} got\n'.format(testname))
            self.dump_orgusers(qset)
            sys.stderr.write('\n')

        self.assertEqual(got, expected, testname)
        return


    ########################################################################
    #                       Tests
    ########################################################################

#-------------------------------------------------------------------
#       Test initial state is what we expect
#-------------------------------------------------------------------

    def test00_orgldap_noop(self):
        """Test that initial values are what we expect"""
        testname='Initial orgs for wilbur'
        user = User.objects.get(username='wilbur')
        uprof = user.userprofile
        qset = OrganizationUser.objects.filter(user=uprof)
        got = self.orgusers_to_dicts(qset)
        expected = WILBUR_ORGS_INITIAL
        self.assertEqual(got, expected, testname)
        return

#-------------------------------------------------------------------
#       Tests of set_organizations_for_user
#-------------------------------------------------------------------

    def test10_setuserorgs_noop(self):
        """Test set_orgs_for_user on noop"""
        testname='set_orgs_for_user: noop'
        username='wilbur'
        orglist = []
        expected = WILBUR_ORGS_INITIAL
        self.do_set_organizations_for_user_test(
                username=username, 
                orglist=orglist,
                expected=expected,
                testname=testname,
            )
        return

    def test10_setuserorgs_noop_duplicates_1stprime(self):
        """Test set_orgs_for_user on noop, with duplicates, def1stprim"""
        testname='set_orgs_for_user: noop, with duplicates + default_1st_primary'
        username='wilbur'
        orglist = [
                'UMD-ENGR-ENAE',
                'UMD-ENGR-ENAE',
                'UMD-CMNS-PHYS',
                'UMD-ENGR-ENAE',
                'UMD-ENGR-ENAE',
                'UMD-CMNS-PHYS',
                'UMD-CMNS-PHYS',
                'UMD-CMNS-PHYS',
                'UMD-CMNS-PHYS',
                'UMD-ENGR-ENAE',
            ]
        expected = WILBUR_ORGS_INITIAL
        self.do_set_organizations_for_user_test(
                username=username, 
                orglist=orglist,
                expected=expected,
                testname=testname,
                default_first_primary=True,
            )
        return

    def test10_setuserorgs_noop_duplicates_delete(self):
        """Test set_orgs_for_user on noop, with duplicates, delete"""
        testname='set_orgs_for_user: noop, with duplicates + delete'
        username='wilbur'
        orglist = [
                'UMD-ENGR-ENAE',
                'UMD-ENGR-ENAE',
                'UMD-CMNS-PHYS',
                'UMD-ENGR-ENAE',
                'UMD-ENGR-ENAE',
                'UMD-CMNS-PHYS',
                'UMD-CMNS-PHYS',
                'UMD-CMNS-PHYS',
                'UMD-CMNS-PHYS',
                'UMD-ENGR-ENAE',
            ]
        expected = WILBUR_ORGS_INITIAL
        self.do_set_organizations_for_user_test(
                username=username, 
                orglist=orglist,
                expected=expected,
                testname=testname,
                delete=True,
            )
        return

    def test10_setuserorgs_noop_duplicates(self):
        """Test set_orgs_for_user on noop, with duplicates"""
        testname='set_orgs_for_user: noop'
        username='wilbur'
        orglist = [
                'UMD-ENGR-ENAE',
                'UMD-CMNS-PHYS',
                'UMD-CMNS-PHYS',
                'UMD-CMNS-PHYS',
                'UMD-ENGR-ENAE',
                'UMD-CMNS-PHYS',
                'UMD-ENGR-ENAE',
                'UMD-ENGR-ENAE',
                'UMD-CMNS-PHYS',
                'UMD-CMNS-PHYS',
                'UMD-CMNS-PHYS',
                'UMD-CMNS-PHYS',
                'UMD-ENGR-ENAE',
            ]
        expected = WILBUR_ORGS_INITIAL
        self.do_set_organizations_for_user_test(
                username=username, 
                orglist=orglist,
                expected=expected,
                testname=testname,
            )
        return

    def test10_setuserorgs_new_secondary(self):
        """Test set_orgs_for_user with new secondary"""
        testname='set_orgs_for_user: new secondary'
        username='wilbur'
        orglist = [ 'UMD-CMNS-ASTR', ]
        expected = WILBUR_ORGS_PLUS_ASTR
        self.do_set_organizations_for_user_test(
                username=username, 
                orglist=orglist,
                expected=expected,
                testname=testname,
            )
        return

    def test10_setuserorgs_new_secondary_delete(self):
        """Test set_orgs_for_user with new secondary, delete"""
        testname='set_orgs_for_user: new secondary, delete'
        username='wilbur'
        orglist = [ 'UMD-CMNS-ASTR', ]
        expected = [ WILBUR_ASTR_SECONDARY ]
        self.do_set_organizations_for_user_test(
                username=username, 
                orglist=orglist,
                expected=expected,
                testname=testname,
                delete=True,
            )
        return

    def test10_setuserorgs_old_secondary_delete(self):
        """Test set_orgs_for_user with old secondary, delete"""
        testname='set_orgs_for_user: old secondary, delete'
        username='wilbur'
        orglist = [ 'UMD-CMNS-PHYS', ]
        expected = [ WILBUR_PHYS_SECONDARY ]
        self.do_set_organizations_for_user_test(
                username=username, 
                orglist=orglist,
                expected=expected,
                testname=testname,
                delete=True,
            )
        return

    def test10_setuserorgs_old_primary_delete(self):
        """Test set_orgs_for_user with old primary, delete"""
        testname='set_orgs_for_user: old primary, delete'
        username='wilbur'
        orglist = [ 'UMD-ENGR-ENAE', ]
        expected = [ WILBUR_ENAE_PRIMARY ]
        self.do_set_organizations_for_user_test(
                username=username, 
                orglist=orglist,
                expected=expected,
                testname=testname,
                delete=True,
            )
        return

    def test10_setuserorgs_new_primary_multiple1(self):
        """Test set_orgs_for_user with new primary, multiple times (1)"""
        testname='set_orgs_for_user: new primary, multiple times (1)'
        username='wilbur'
        orglist = [ 
                {   'organization': 'UMD-CMNS-ASTR', 
                    'is_primary': True,
                },
                {   'organization': 'UMD-CMNS-ASTR', 
                    'is_primary': True,
                },
                {   'organization': 'UMD-CMNS-ASTR', 
                    'is_primary': True,
                },
                ]
        expected = [ 
                WILBUR_ASTR_PRIMARY,
                WILBUR_ENAE_SECONDARY,
                WILBUR_PHYS_SECONDARY,
            ]
        self.do_set_organizations_for_user_test(
                username=username, 
                orglist=orglist,
                expected=expected,
                testname=testname,
            )
        return

    def test10_setuserorgs_new_primary_multiple2(self):
        """Test set_orgs_for_user with new primary, multiple times (2)"""
        testname='set_orgs_for_user: new primary, multiple times (2)'
        username='wilbur'
        orglist = [ 
                {   'organization': 'UMD-CMNS-ASTR', 
                    'is_primary': True,
                },
                {   'organization': 'UMD-CMNS-ASTR', 
                    'is_primary': True,
                },
                {   'organization': 'UMD-CMNS-ASTR', 
                    'is_primary': False,
                },
                ]
        expected = [ 
                WILBUR_ASTR_SECONDARY,
                WILBUR_ENAE_SECONDARY,
                WILBUR_PHYS_SECONDARY,
            ]
        self.do_set_organizations_for_user_test(
                username=username, 
                orglist=orglist,
                expected=expected,
                testname=testname,
            )
        return

    def test10_setuserorgs_new_primary_multiple3(self):
        """Test set_orgs_for_user with new primary, multiple times (3)"""
        testname='set_orgs_for_user: new primary, multiple times (3)'
        username='wilbur'
        orglist = [ 
                {   'organization': 'UMD-CMNS-ASTR', 
                    'is_primary': True,
                },
                {   'organization': 'UMD-CMNS-ASTR', 
                    'is_primary': True,
                },
                {   'organization': 'UMD-CMNS-ASTR', 
                },
                ]
        expected = [ 
                WILBUR_ASTR_PRIMARY,
                WILBUR_ENAE_SECONDARY,
                WILBUR_PHYS_SECONDARY,
            ]
        self.do_set_organizations_for_user_test(
                username=username, 
                orglist=orglist,
                expected=expected,
                testname=testname,
            )
        return

    def test10_setuserorgs_new_primary_multiple4(self):
        """Test set_orgs_for_user with new primary, multiple times (4)"""
        testname='set_orgs_for_user: new primary, multiple times (4)'
        username='wilbur'
        orglist = [ 
                {   'organization': 'UMD-CMNS-ASTR', 
                    'is_primary': True,
                },
                {   'organization': 'UMD-CMNS-ASTR', 
                    'is_primary': True,
                },
                'UMD-CMNS-ASTR', 
                ]
        expected = [ 
                WILBUR_ASTR_PRIMARY,
                WILBUR_ENAE_SECONDARY,
                WILBUR_PHYS_SECONDARY,
            ]
        self.do_set_organizations_for_user_test(
                username=username, 
                orglist=orglist,
                expected=expected,
                testname=testname,
            )
        return

#-------------------------------------------------------------------
#       Tests of set_organizations_for_user
#-------------------------------------------------------------------

    def test20_setprojorgs_noop(self):
        """Test set_orgs_for_proj on noop"""
        testname='set_orgs_for_proj: noop'
        project = FLIGHT_PROJ
        orglist = []
        expected = FLIGHT_ORGS_INITIAL
        self.do_set_organizations_for_proj_test(
                project=project,
                orglist=orglist,
                expected=expected,
                testname=testname,
            )
        return

    def test20_setprojorgs_noop_duplicates_1stprime(self):
        """Test set_orgs_for_proj on noop, with duplicates, def1stprim"""
        testname='set_orgs_for_proj: noop, with duplicates + default_1st_primary'
        project = FLIGHT_PROJ
        orglist = [
                'UMD-ENGR-ENAE',
                'UMD-ENGR-ENAE',
                'UMD-CMNS-PHYS',
                'UMD-ENGR-ENAE',
                'UMD-ENGR-ENAE',
                'UMD-CMNS-PHYS',
                'UMD-CMNS-PHYS',
                'UMD-CMNS-PHYS',
                'UMD-CMNS-PHYS',
                'UMD-ENGR-ENAE',
            ]
        expected = FLIGHT_ORGS_INITIAL
        self.do_set_organizations_for_proj_test(
                project=project,
                orglist=orglist,
                expected=expected,
                testname=testname,
                default_first_primary=True,
            )
        return

    def test20_setprojorgs_noop_duplicates_delete(self):
        """Test set_orgs_for_proj on noop, with duplicates, delete"""
        testname='set_orgs_for_proj: noop, with duplicates + delete'
        project = FLIGHT_PROJ
        orglist = [
                'UMD-ENGR-ENAE',
                'UMD-ENGR-ENAE',
                'UMD-CMNS-PHYS',
                'UMD-ENGR-ENAE',
                'UMD-ENGR-ENAE',
                'UMD-CMNS-PHYS',
                'UMD-CMNS-PHYS',
                'UMD-CMNS-PHYS',
                'UMD-CMNS-PHYS',
                'UMD-ENGR-ENAE',
            ]
        expected = FLIGHT_ORGS_INITIAL
        self.do_set_organizations_for_proj_test(
                project=project,
                orglist=orglist,
                expected=expected,
                testname=testname,
                delete=True,
            )
        return

    def test20_setprojorgs_noop_duplicates(self):
        """Test set_orgs_for_proj on noop, with duplicates"""
        testname='set_orgs_for_proj: noop'
        project = FLIGHT_PROJ
        orglist = [
                'UMD-ENGR-ENAE',
                'UMD-CMNS-PHYS',
                'UMD-CMNS-PHYS',
                'UMD-CMNS-PHYS',
                'UMD-ENGR-ENAE',
                'UMD-CMNS-PHYS',
                'UMD-ENGR-ENAE',
                'UMD-ENGR-ENAE',
                'UMD-CMNS-PHYS',
                'UMD-CMNS-PHYS',
                'UMD-CMNS-PHYS',
                'UMD-CMNS-PHYS',
                'UMD-ENGR-ENAE',
            ]
        expected = FLIGHT_ORGS_INITIAL
        self.do_set_organizations_for_proj_test(
                project=project,
                orglist=orglist,
                expected=expected,
                testname=testname,
            )
        return

    def test20_setprojorgs_new_secondary(self):
        """Test set_orgs_for_proj with new secondary"""
        testname='set_orgs_for_proj: new secondary'
        project = FLIGHT_PROJ
        orglist = [ 'UMD-CMNS-ASTR', ]
        expected = FLIGHT_ORGS_PLUS_ASTR
        self.do_set_organizations_for_proj_test(
                project=project,
                orglist=orglist,
                expected=expected,
                testname=testname,
            )
        return

    def test20_setprojorgs_new_secondary_delete(self):
        """Test set_orgs_for_proj with new secondary, delete"""
        testname='set_orgs_for_proj: new secondary, delete'
        project = FLIGHT_PROJ
        orglist = [ 'UMD-CMNS-ASTR', ]
        expected = [ FLIGHT_ASTR_SECONDARY ]
        self.do_set_organizations_for_proj_test(
                project=project,
                orglist=orglist,
                expected=expected,
                testname=testname,
                delete=True,
            )
        return

    def test20_setprojorgs_old_secondary_delete(self):
        """Test set_orgs_for_proj with old secondary, delete"""
        testname='set_orgs_for_proj: old secondary, delete'
        project = FLIGHT_PROJ
        orglist = [ 'UMD-CMNS-PHYS', ]
        expected = [ FLIGHT_PHYS_SECONDARY ]
        self.do_set_organizations_for_proj_test(
                project=project,
                orglist=orglist,
                expected=expected,
                testname=testname,
                delete=True,
            )
        return

    def test20_setprojorgs_old_primary_delete(self):
        """Test set_orgs_for_proj with old primary, delete"""
        testname='set_orgs_for_proj: old primary, delete'
        project = FLIGHT_PROJ
        orglist = [ 'UMD-ENGR-ENAE', ]
        expected = [ FLIGHT_ENAE_PRIMARY ]
        self.do_set_organizations_for_proj_test(
                project=project,
                orglist=orglist,
                expected=expected,
                testname=testname,
                delete=True,
            )
        return

    def test20_setprojorgs_new_primary_multiple1(self):
        """Test set_orgs_for_proj with new primary, multiple times (1)"""
        testname='set_orgs_for_proj: new primary, multiple times (1)'
        project = FLIGHT_PROJ
        orglist = [ 
                {   'organization': 'UMD-CMNS-ASTR', 
                    'is_primary': True,
                },
                {   'organization': 'UMD-CMNS-ASTR', 
                    'is_primary': True,
                },
                {   'organization': 'UMD-CMNS-ASTR', 
                    'is_primary': True,
                },
                ]
        expected = [ 
                FLIGHT_ASTR_PRIMARY,
                FLIGHT_ENAE_SECONDARY,
                FLIGHT_PHYS_SECONDARY,
            ]
        self.do_set_organizations_for_proj_test(
                project=project,
                orglist=orglist,
                expected=expected,
                testname=testname,
            )
        return

    def test20_setprojorgs_new_primary_multiple2(self):
        """Test set_orgs_for_proj with new primary, multiple times (2)"""
        testname='set_orgs_for_proj: new primary, multiple times (2)'
        project = FLIGHT_PROJ
        orglist = [ 
                {   'organization': 'UMD-CMNS-ASTR', 
                    'is_primary': True,
                },
                {   'organization': 'UMD-CMNS-ASTR', 
                    'is_primary': True,
                },
                {   'organization': 'UMD-CMNS-ASTR', 
                    'is_primary': False,
                },
                ]
        expected = [ 
                FLIGHT_ASTR_SECONDARY,
                FLIGHT_ENAE_SECONDARY,
                FLIGHT_PHYS_SECONDARY,
            ]
        self.do_set_organizations_for_proj_test(
                project=project,
                orglist=orglist,
                expected=expected,
                testname=testname,
            )
        return

    def test20_setprojorgs_new_primary_multiple3(self):
        """Test set_orgs_for_proj with new primary, multiple times (3)"""
        testname='set_orgs_for_proj: new primary, multiple times (3)'
        project = FLIGHT_PROJ
        orglist = [ 
                {   'organization': 'UMD-CMNS-ASTR', 
                    'is_primary': True,
                },
                {   'organization': 'UMD-CMNS-ASTR', 
                    'is_primary': True,
                },
                {   'organization': 'UMD-CMNS-ASTR', 
                },
                ]
        expected = [ 
                FLIGHT_ASTR_PRIMARY,
                FLIGHT_ENAE_SECONDARY,
                FLIGHT_PHYS_SECONDARY,
            ]
        self.do_set_organizations_for_proj_test(
                project=project,
                orglist=orglist,
                expected=expected,
                testname=testname,
            )
        return

    def test20_setprojorgs_new_primary_multiple4(self):
        """Test set_orgs_for_proj with new primary, multiple times (4)"""
        testname='set_orgs_for_proj: new primary, multiple times (4)'
        project = FLIGHT_PROJ
        orglist = [ 
                {   'organization': 'UMD-CMNS-ASTR', 
                    'is_primary': True,
                },
                {   'organization': 'UMD-CMNS-ASTR', 
                    'is_primary': True,
                },
                'UMD-CMNS-ASTR', 
                ]
        expected = [ 
                FLIGHT_ASTR_PRIMARY,
                FLIGHT_ENAE_SECONDARY,
                FLIGHT_PHYS_SECONDARY,
            ]
        self.do_set_organizations_for_proj_test(
                project=project,
                orglist=orglist,
                expected=expected,
                testname=testname,
            )
        return

#-------------------------------------------------------------------
#       Tests of populate_user_organizations
#-------------------------------------------------------------------

    def test30_orgldap_noop_handler(self):
        """Test doing a noop through the handler"""
        testname='Noop through handler'
        varhash = {
                'orgsignals':
                { 
                    'ORGANIZATION_LDAP_USER_ORG_ATTRIBUTE': 'exDepartment',
                    'ORGANIZATION_LDAP_USER_PORG_ATTRIBUTE': 'exPrimaryDepartment',
                    'ORGANIZATION_LDAP_USER_DELETE_MISSING': False,
                    'ORGANIZATION_LDAP_USER_CREATE_PLACEHOLDERS': True,
                },
            }
        username='wilbur'
        attribs = {}
        expected = WILBUR_ORGS_INITIAL
        self.do_populate_user_test(
                varhash=varhash,
                username=username,
                attribs=attribs,
                expected=expected,
                testname=testname,
            )
        return

    def test30_orgldap_existing_secondary(self):
        """Test adding an existing secondary to user"""
        testname='Existing secondary org'
        varhash = {
                'orgsignals':
                { 
                    'ORGANIZATION_LDAP_USER_ORG_ATTRIBUTE': 'exDepartment',
                    'ORGANIZATION_LDAP_USER_PORG_ATTRIBUTE': 'exPrimaryDepartment',
                    'ORGANIZATION_LDAP_USER_DELETE_MISSING': False,
                    'ORGANIZATION_LDAP_USER_CREATE_PLACEHOLDERS': True,
                },
            }
        username='wilbur'
        attribs = {
                'exDepartment': [
                        LDAPSTR_PHYS2,
                    ],
                }
        expected = WILBUR_ORGS_INITIAL
        self.do_populate_user_test(
                varhash=varhash,
                username=username,
                attribs=attribs,
                expected=expected,
                testname=testname,
            )
        return

    def test30_orgldap_existing_primary(self):
        """Test adding an existing primary to user"""
        testname='Existing primary org'
        varhash = {
                'orgsignals':
                { 
                    'ORGANIZATION_LDAP_USER_ORG_ATTRIBUTE': 'exDepartment',
                    'ORGANIZATION_LDAP_USER_PORG_ATTRIBUTE': 'exPrimaryDepartment',
                    'ORGANIZATION_LDAP_USER_DELETE_MISSING': False,
                    'ORGANIZATION_LDAP_USER_CREATE_PLACEHOLDERS': True,
                },
            }
        username='wilbur'
        attribs = {
                'exPrimaryDepartment': [
                        LDAPSTR_ENAE
                    ],
                }
        expected = WILBUR_ORGS_INITIAL
        self.do_populate_user_test(
                varhash=varhash,
                username=username,
                attribs=attribs,
                expected=expected,
                testname=testname,
            )
        return

    def test30_orgldap_existing_primary_secondary(self):
        """Test adding an existing primary + secondary to user"""
        testname='Existing primary + secondary org'
        varhash = {
                'orgsignals':
                { 
                    'ORGANIZATION_LDAP_USER_ORG_ATTRIBUTE': 'exDepartment',
                    'ORGANIZATION_LDAP_USER_PORG_ATTRIBUTE': 'exPrimaryDepartment',
                    'ORGANIZATION_LDAP_USER_DELETE_MISSING': False,
                    'ORGANIZATION_LDAP_USER_CREATE_PLACEHOLDERS': True,
                },
            }
        username='wilbur'
        attribs = {
                'exPrimaryDepartment': [
                        LDAPSTR_ENAE
                    ],
                'exDepartment': [
                        LDAPSTR_PHYS2,
                        LDAPSTR_PHYS3,
                        LDAPSTR_PHYS,
                    ],
                }
        expected = WILBUR_ORGS_INITIAL
        self.do_populate_user_test(
                varhash=varhash,
                username=username,
                attribs=attribs,
                expected=expected,
                testname=testname,
            )
        return

    def test30_orgldap_existing_primary_as_secondary(self):
        """Test adding an existing primary as secondary"""
        testname='Existing primary as secondary org'
        varhash = {
                'orgsignals':
                { 
                    'ORGANIZATION_LDAP_USER_ORG_ATTRIBUTE': 'exDepartment',
                    'ORGANIZATION_LDAP_USER_PORG_ATTRIBUTE': 'exPrimaryDepartment',
                    'ORGANIZATION_LDAP_USER_DELETE_MISSING': False,
                    'ORGANIZATION_LDAP_USER_CREATE_PLACEHOLDERS': True,
                },
            }
        username='wilbur'
        attribs = {
                'exDepartment': [
                        LDAPSTR_ENAE
                    ],
                }
        expected = WILBUR_ORGS_INITIAL
        self.do_populate_user_test(
                varhash=varhash,
                username=username,
                attribs=attribs,
                expected=expected,
                testname=testname,
            )
        return

    def test30_orgldap_existing_secondary_as_primary(self):
        """Test adding an existing secondary as primary to user"""
        testname='Existing secondary as primary org'
        varhash = {
                'orgsignals':
                { 
                    'ORGANIZATION_LDAP_USER_ORG_ATTRIBUTE': 'exDepartment',
                    'ORGANIZATION_LDAP_USER_PORG_ATTRIBUTE': 'exPrimaryDepartment',
                    'ORGANIZATION_LDAP_USER_DELETE_MISSING': False,
                    'ORGANIZATION_LDAP_USER_CREATE_PLACEHOLDERS': True,
                },
            }
        username='wilbur'
        attribs = {
                'exPrimaryDepartment': [
                        LDAPSTR_PHYS3,
                    ],
                }
        expected = WILBUR_ORGS_SWAP_PRIMARY

        self.do_populate_user_test(
                varhash=varhash,
                username=username,
                attribs=attribs,
                expected=expected,
                testname=testname,
            )
        return

    def test30_orgldap_new_secondary(self):
        """Test adding a new secondary to user"""
        testname='New secondary'
        varhash = {
                'orgsignals':
                { 
                    'ORGANIZATION_LDAP_USER_ORG_ATTRIBUTE': 'exDepartment',
                    'ORGANIZATION_LDAP_USER_PORG_ATTRIBUTE': 'exPrimaryDepartment',
                    'ORGANIZATION_LDAP_USER_DELETE_MISSING': False,
                    'ORGANIZATION_LDAP_USER_CREATE_PLACEHOLDERS': True,
                },
            }
        username='wilbur'
        attribs = {
                'exDepartment': [
                        LDAPSTR_ASTR
                    ],
                }
        expected = WILBUR_ORGS_PLUS_ASTR
        self.do_populate_user_test(
                varhash=varhash,
                username=username,
                attribs=attribs,
                expected=expected,
                testname=testname,
            )
        return

    def test30_orgldap_new_primary(self):
        """Test adding a new primary to user"""
        testname='New primary'
        varhash = {
                'orgsignals':
                { 
                    'ORGANIZATION_LDAP_USER_ORG_ATTRIBUTE': 'exDepartment',
                    'ORGANIZATION_LDAP_USER_PORG_ATTRIBUTE': 'exPrimaryDepartment',
                    'ORGANIZATION_LDAP_USER_DELETE_MISSING': False,
                    'ORGANIZATION_LDAP_USER_CREATE_PLACEHOLDERS': True,
                },
            }
        username='wilbur'
        attribs = {
                'exPrimaryDepartment': [
                        LDAPSTR_ASTR
                    ],
                }
        expected = [
                WILBUR_ASTR_PRIMARY,
                WILBUR_ENAE_SECONDARY,
                WILBUR_PHYS_SECONDARY,
            ]
        self.do_populate_user_test(
                varhash=varhash,
                username=username,
                attribs=attribs,
                expected=expected,
                testname=testname,
            )
        return

    def test30_orgldap_new_primary2(self):
        """Test adding a new primary to user (2)"""
        testname='New primary2'
        varhash = {
                'orgsignals':
                { 
                    'ORGANIZATION_LDAP_USER_ORG_ATTRIBUTE': 'exDepartment',
                    'ORGANIZATION_LDAP_USER_PORG_ATTRIBUTE': 'exPrimaryDepartment',
                    'ORGANIZATION_LDAP_USER_DELETE_MISSING': False,
                    'ORGANIZATION_LDAP_USER_CREATE_PLACEHOLDERS': True,
                },
            }
        username='wilbur'
        attribs = {
                'exPrimaryDepartment': [
                        LDAPSTR_ASTR
                    ],
                'exDepartment': [
                        LDAPSTR_ASTR
                    ],
                }
        expected = [
                WILBUR_ASTR_PRIMARY,
                WILBUR_ENAE_SECONDARY,
                WILBUR_PHYS_SECONDARY,
            ]
        self.do_populate_user_test(
                varhash=varhash,
                username=username,
                attribs=attribs,
                expected=expected,
                testname=testname,
            )
        return

    def test30_orgldap_new_secondary_delete1(self):
        """Test adding a new secondary + delete (1)"""
        testname='New secondary with delete (1)'
        varhash = {
                'orgsignals':
                { 
                    'ORGANIZATION_LDAP_USER_ORG_ATTRIBUTE': 'exDepartment',
                    'ORGANIZATION_LDAP_USER_PORG_ATTRIBUTE': 'exPrimaryDepartment',
                    'ORGANIZATION_LDAP_USER_DELETE_MISSING': True,
                    'ORGANIZATION_LDAP_USER_CREATE_PLACEHOLDERS': True,
                },
            }
        username='wilbur'
        attribs = {
                'exPrimaryDepartment': [
                        LDAPSTR_ENAE,
                    ],
                'exDepartment': [
                        LDAPSTR_ASTR,
                        LDAPSTR_PHYS,
                    ],
                }
        expected = [
                WILBUR_ENAE_PRIMARY,
                WILBUR_ASTR_SECONDARY,
                WILBUR_PHYS_SECONDARY,
            ]
        self.do_populate_user_test(
                varhash=varhash,
                username=username,
                attribs=attribs,
                expected=expected,
                testname=testname,
            )
        return

    def test30_orgldap_new_secondary_delete2(self):
        """Test adding a new secondary + delete (2)"""
        testname='New secondary with delete (2)'
        varhash = {
                'orgsignals':
                { 
                    'ORGANIZATION_LDAP_USER_ORG_ATTRIBUTE': 'exDepartment',
                    'ORGANIZATION_LDAP_USER_PORG_ATTRIBUTE': 'exPrimaryDepartment',
                    'ORGANIZATION_LDAP_USER_DELETE_MISSING': True,
                    'ORGANIZATION_LDAP_USER_CREATE_PLACEHOLDERS': True,
                },
            }
        username='wilbur'
        attribs = {
                'exPrimaryDepartment': [
                        LDAPSTR_ENAE,
                        LDAPSTR_ASTR,
                        LDAPSTR_PHYS,
                    ],
                'exDepartment': [
                        LDAPSTR_ASTR,
                        LDAPSTR_PHYS,
                        LDAPSTR_ENAE,
                    ],
                }
        expected = [
                WILBUR_ENAE_PRIMARY,
                WILBUR_ASTR_SECONDARY,
                WILBUR_PHYS_SECONDARY,
            ]
        self.do_populate_user_test(
                varhash=varhash,
                username=username,
                attribs=attribs,
                expected=expected,
                testname=testname,
            )
        return

    def test30_orgldap_new_primary_delete1(self):
        """Test adding a new primary + delete (1)"""
        testname='New primary with delete (1)'
        varhash = {
                'orgsignals':
                { 
                    'ORGANIZATION_LDAP_USER_ORG_ATTRIBUTE': 'exDepartment',
                    'ORGANIZATION_LDAP_USER_PORG_ATTRIBUTE': 'exPrimaryDepartment',
                    'ORGANIZATION_LDAP_USER_DELETE_MISSING': True,
                    'ORGANIZATION_LDAP_USER_CREATE_PLACEHOLDERS': True,
                },
            }
        username='wilbur'
        attribs = {
                'exPrimaryDepartment': [
                        LDAPSTR_ASTR,
                        LDAPSTR_ENAE,
                        LDAPSTR_PHYS,
                    ],
                'exDepartment': [
                        LDAPSTR_ASTR,
                        LDAPSTR_PHYS,
                        LDAPSTR_ENAE,
                    ],
                }
        expected = [
                WILBUR_ASTR_PRIMARY,
                WILBUR_ENAE_SECONDARY,
                WILBUR_PHYS_SECONDARY,
            ]
        self.do_populate_user_test(
                varhash=varhash,
                username=username,
                attribs=attribs,
                expected=expected,
                testname=testname,
            )
        return

    def test30_orgldap_new_unknown_secondary_nocreate(self):
        """Test adding a new unknown secondary, no placeholders"""
        testname='New unknown secondary, no placeholders'
        varhash = {
                'orgsignals':
                { 
                    'ORGANIZATION_LDAP_USER_ORG_ATTRIBUTE': 'exDepartment',
                    'ORGANIZATION_LDAP_USER_PORG_ATTRIBUTE': 'exPrimaryDepartment',
                    'ORGANIZATION_LDAP_USER_DELETE_MISSING': False,
                    'ORGANIZATION_LDAP_USER_CREATE_PLACEHOLDERS': False
                },
            }
        username='wilbur'
        attribs = {
                'exDepartment': [
                        'TEST-Dept of Redundancy Dept',
                    ],
                }
        expected = [
                WILBUR_ENAE_PRIMARY,
                WILBUR_PHYS_SECONDARY,
            ]
        self.do_populate_user_test(
                varhash=varhash,
                username=username,
                attribs=attribs,
                expected=expected,
                testname=testname,
            )
        return

    def test30_orgldap_new_unknown_secondary_create(self):
        """Test adding a new unknown secondary, + placeholders"""
        testname='New unknown secondary, + placeholders'
        varhash = {
                'orgsignals':
                { 
                    'ORGANIZATION_LDAP_USER_ORG_ATTRIBUTE': 'exDepartment',
                    'ORGANIZATION_LDAP_USER_PORG_ATTRIBUTE': 'exPrimaryDepartment',
                    'ORGANIZATION_LDAP_USER_DELETE_MISSING': False,
                    'ORGANIZATION_LDAP_USER_CREATE_PLACEHOLDERS': True
                },
            }
        username='wilbur'
        attribs = {
                'exDepartment': [
                        'TEST-Dept of Redundancy Dept',
                    ],
                }
        expected = [
                WILBUR_ENAE_PRIMARY,
                WILBUR_PHYS_SECONDARY,
                WILBUR_UNKNOWN_SECONDARY,
            ]

        self.do_populate_user_test(
                varhash=varhash,
                username=username,
                attribs=attribs,
                expected=expected,
                testname=testname,
                expect_new_unknown=True,
            )
        return

    def test30_orgldap_new_unknown_primary_nocreate(self):
        """Test adding a new unknown primary, no placeholders"""
        testname='New unknown primary, no placeholders'
        varhash = {
                'orgsignals':
                { 
                    'ORGANIZATION_LDAP_USER_ORG_ATTRIBUTE': 'exDepartment',
                    'ORGANIZATION_LDAP_USER_PORG_ATTRIBUTE': 'exPrimaryDepartment',
                    'ORGANIZATION_LDAP_USER_DELETE_MISSING': False,
                    'ORGANIZATION_LDAP_USER_CREATE_PLACEHOLDERS': False
                },
            }
        username='wilbur'
        attribs = {
                'exPrimaryDepartment': [
                        'TEST-Dept of Redundancy Dept',
                    ],
                }
        expected = [
                WILBUR_ENAE_PRIMARY,
                WILBUR_PHYS_SECONDARY,
            ]
        self.do_populate_user_test(
                varhash=varhash,
                username=username,
                attribs=attribs,
                expected=expected,
                testname=testname,
            )
        return

    def test30_orgldap_new_unknown_primary_create(self):
        """Test adding a new unknown primary, + placeholders"""
        testname='New unknown primary, + placeholders'
        varhash = {
                'orgsignals':
                { 
                    'ORGANIZATION_LDAP_USER_ORG_ATTRIBUTE': 'exDepartment',
                    'ORGANIZATION_LDAP_USER_PORG_ATTRIBUTE': 'exPrimaryDepartment',
                    'ORGANIZATION_LDAP_USER_DELETE_MISSING': False,
                    'ORGANIZATION_LDAP_USER_CREATE_PLACEHOLDERS': True
                },
            }
        username='wilbur'
        attribs = {
                'exPrimaryDepartment': [
                        'TEST-Dept of Redundancy Dept',
                    ],
                }
        expected = [
                WILBUR_UNKNOWN_PRIMARY,
                WILBUR_ENAE_SECONDARY,
                WILBUR_PHYS_SECONDARY,
            ]

        self.do_populate_user_test(
                varhash=varhash,
                username=username,
                attribs=attribs,
                expected=expected,
                testname=testname,
                expect_new_unknown=True,
            )
        return


