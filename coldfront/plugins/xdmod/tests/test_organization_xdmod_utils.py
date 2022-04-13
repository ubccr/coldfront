import sys

from django.core.exceptions import ValidationError 
from django.db.models import ProtectedError
#from django.test import TestCase

from coldfront.core.utils.libtest import ConfigChangingTestCase
from coldfront.core.organization.models import (
        OrganizationLevel,
        Organization,
        )
from coldfront.core.allocation.models import (
        Allocation,
        AllocationAttribute,
        )
import coldfront.plugins.xdmod.utils as xdmod
from django.contrib.auth.models import User

# Set VERBOSE_TEST_OUTPUT to generate verbose output for
# a class of tests.  Allowed strings are:
#   orglevel: for tests using do_xdmod_orglevel_hierarchy_list_test
#   hier_json: for tests using do_hierarchy_json_test
#   hier_csv: for tests using do_hierarchy_csv_test
#   group2hier: for tests using do_group2hierarchy_test
#   names_csv: for tests using do_names_csv_user_test
# Leave empty to disable verbose output
VERBOSE_TEST_OUTPUT = set()
#VERBOSE_TEST_OUTPUT.add( 'orglevel' )
#VERBOSE_TEST_OUTPUT.add( 'hier_json' )
#VERBOSE_TEST_OUTPUT.add( 'hier_csv' )
#VERBOSE_TEST_OUTPUT.add( 'group2hier' )
#VERBOSE_TEST_OUTPUT.add( 'names_csv' )

EXPECTED_DEPT_ORGLEV = {   
        'name': 'Department',
        'level': 20,
        'export_to_xdmod': True,
        'parent': 'College',
    }
EXPECTED_COLL_ORGLEV = {   
       'name': 'College',
        'level': 30,
        'export_to_xdmod': True,
        'parent': 'University',
    }
EXPECTED_UNIV_ORGLEV = {   
        'name': 'University',
        'level': 40,
        'export_to_xdmod': True,
        'parent': None,
    }

# Alphabetical by code (not fullcode)
EXPECTED_ORGLIST_UNIV = [
        ('UMB', 'UMD Baltimore', None),
        ('UMD', 'UMCP', None),
        ('Unknown', 'Unknown', None),
    ]

# Alphabetical by code (not fullcode)
EXPECTED_ORGLIST_COLL = [
        ('UMD-CMNS', 'CMNS', 'UMD'),
        ('UMD-ENGR', 'Engineering', 'UMD'),
        ('UMB-SoD', 'Dentistry', 'UMB'),
        ('UMB-SoM', 'Medicine', 'UMB'),
    ]

# Alphabetical by code (not fullcode)
EXPECTED_ORGLIST_DEPT = [
        ('UMD-CMNS-ASTR', 'Astronomy', 'UMD-CMNS'),
        ('UMD-ENGR-ENAE', 'Aeronautical Eng', 'UMD-ENGR'),
        ('UMD-ENGR-ENMA', 'Materials Eng', 'UMD-ENGR'),
        ('UMB-SoD-NeuPain', 'Neural and Pain', 'UMB-SoD'),
        ('UMD-CMNS-PHYS', 'Physics', 'UMD-CMNS'),
        ('UMB-SoD-Perio', 'Periodontics', 'UMB-SoD'),
        ('UMB-SoM-Psych', 'Psychiatry', 'UMB-SoM'),
        ('UMB-SoM-Surg', 'Surgery', 'UMB-SoM'),
    ]

# Alphabetical by ???
EXPECTED_ORGLIST_PROJ_NOALLOC_PI = [
        ( 'proj-einstein-prj', 'Gravitational Studies', 'UMD-CMNS-PHYS'),
        ( 'proj-freud-prj', 'Artificial Id', 'UMB-SoM-Psych'),
        ( 'proj-hawkeye-prj', 'Meatball Surgery', 'UMB-SoM-Surg'),
        ( 'proj-orville-prj', 'Hyposonic Flight', 'UMD-ENGR-ENAE'),
    ]

EXPECTED_ORGLIST_PROJ_NOALLOC_ATTRIB = [
        ( 'proj-einstein-prj', 'Gravitational Studies', 'UMD-CMNS-PHYS'),
        ( 'proj-freud-prj', 'Artificial Id', 'UMB-SoM-Psych'),
        ( 'proj-hawkeye-prj', 'Meatball Surgery', 'UMB-SoM-Surg'),
        ( 'wright-proj', 'Hyposonic Flight', 'UMD-ENGR-ENAE'),
    ]

EXPECTED_ORGLIST_PROJ_NOALLOC_ATTRIB_SLURM = [
        ( 'proj-einstein-alloc', 'Gravitational Studies', 'UMD-CMNS-PHYS'),
        ( 'proj-freud-alloc', 'Artificial Id', 'UMB-SoM-Psych'),
        ( 'proj-hawkeye-alloc', 'Meatball Surgery', 'UMB-SoM-Surg'),
        ( 'wright-proj', 'Hyposonic Flight', 'UMD-ENGR-ENAE'),
    ]

EXPECTED_ORGLIST_PROJ_NOALLOC_TITLE = [
        ( 'proj-Gravitational_Studies', 'Gravitational Studies', 'UMD-CMNS-PHYS'),
        ( 'proj-Artificial_Id', 'Artificial Id', 'UMB-SoM-Psych'),
        ( 'proj-Meatball_Surgery', 'Meatball Surgery', 'UMB-SoM-Surg'),
        ( 'proj-Hyposonic_Flight', 'Hyposonic Flight', 'UMD-ENGR-ENAE'),
    ]

# Take last allocation name
EXPECTED_ORGLIST_PROJ_NOALLOC_PSLURM = [
        ( 'proj-einstein-alloc', 'Gravitational Studies', 'UMD-CMNS-PHYS'),
        ( 'proj-freud-alloc', 'Artificial Id', 'UMB-SoM-Psych'),
        ( 'proj-hawkeye-alloc', 'Meatball Surgery', 'UMB-SoM-Surg'),
        ( 'proj-wright-alloc', 'Hyposonic Flight', 'UMD-ENGR-ENAE'),
    ]

# Take first allocation name
EXPECTED_ORGLIST_PROJ_NOALLOC_MSLURM = [
        ( 'proj-einstein-alloc', 'Gravitational Studies', 'UMD-CMNS-PHYS'),
        ( 'proj-freud-alloc', 'Artificial Id', 'UMB-SoM-Psych'),
        ( 'proj-hawkeye-alloc', 'Meatball Surgery', 'UMB-SoM-Surg'),
        ( 'proj-orville-alloc', 'Hyposonic Flight', 'UMD-ENGR-ENAE'),
    ]

EXPECTED_ORGLIST_NOPROJ_ALLOC = [
         ( 'alloc-einstein-alloc-suffix', 'alloc-einstein-alloc-suffix', 'UMD-CMNS-PHYS'),
         ( 'hyposonicflight', 'hyposonicflight', 'UMD-ENGR-ENAE'),
         ( 'alloc-orville-alloc-suffix', 'Orville Wright allocation', 'UMD-ENGR-ENAE'),
         ( 'alloc-freud-alloc-suffix', 'alloc-freud-alloc-suffix', 'UMB-SoM-Psych'),
         ( 'alloc-hawkeye-alloc-suffix', 'alloc-hawkeye-alloc-suffix', 'UMB-SoM-Surg'),
    ]

EXPECTED_ORGLIST_PROJ_ALLOC = [
         ( 'alloc-einstein-alloc-suffix', 'alloc-einstein-alloc-suffix', 'proj-einstein-alloc'),
         ( 'hyposonicflight', 'hyposonicflight', 'wright-proj'),
         ( 'alloc-orville-alloc-suffix', 'Orville Wright allocation', 'wright-proj'),
         ( 'alloc-freud-alloc-suffix', 'alloc-freud-alloc-suffix', 'proj-freud-alloc'),
         ( 'alloc-hawkeye-alloc-suffix', 'alloc-hawkeye-alloc-suffix', 'proj-hawkeye-alloc'),
    ]

EXPECTED_G2HIER_DEPT = [
        ('einstein-alloc', 'UMD-CMNS-PHYS'),
        ('wright-alloc', 'UMD-ENGR-ENAE'),
        ('wilbur-alloc', 'UMD-ENGR-ENAE'),
        ('orville-alloc', 'UMD-ENGR-ENAE'),
        ('freud-alloc', 'UMB-SoM-Psych'),
        ('hawkeye-alloc', 'UMB-SoM-Surg'),
    ]

EXPECTED_G2HIER_PROJ = [
        ('einstein-alloc', 'proj-einstein-alloc'),
        ('wright-alloc', 'wright-proj'),
        ('wilbur-alloc', 'wright-proj'),
        ('orville-alloc', 'wright-proj'),
        ('freud-alloc', 'proj-freud-alloc'),
        ('hawkeye-alloc', 'proj-hawkeye-alloc'),
    ]

EXPECTED_G2HIER_ALLOC = [
        ('einstein-alloc', 'alloc-einstein-alloc-suffix'),
        ('wright-alloc', 'hyposonicflight'),
        ('wilbur-alloc', 'hyposonicflight'),
        ('orville-alloc', 'alloc-orville-alloc-suffix'),
        ('freud-alloc', 'alloc-freud-alloc-suffix'),
        ('hawkeye-alloc', 'alloc-hawkeye-alloc-suffix'),
    ]

EXPECTED_NAMES_CSV_USER_DEFAULT = [
        ('einstein', 'Albert', 'Einstein'),
        ('freud', 'Sigmund', 'Freud'),
        ('hawkeye', 'Benjamin', 'Pierce'),
        ('newton', 'Isaac', 'Newton'),
        ('orville', 'Orville', 'Wright'),
        ('wilbur', 'Wilbur', 'Wright'),
    ]

EXPECTED_NAMES_CSV_USER_CUSTOM1 = [
        ('einstein', '', 'Albert Einstein (einstein@example.com)'),
        ('freud', '', 'Sigmund Freud (freud@example.com)'),
        ('hawkeye', '', 'Benjamin Pierce (hawkeye@example.com)'),
        ('newton', '', 'Isaac Newton (newton@example.com)'),
        ('orville', '', 'Orville Wright (orville@example.com)'),
        ('wilbur', '', 'Wilbur Wright (wilbur@example.com)'),
    ]

class Organization2XdmodTest(ConfigChangingTestCase):
    fixtures = ['organization_test_data.json']

    # Helper functions
    def orglevel_to_dict(self, orglevel):
        """Convert an OrgLevel to a dict"""
        if orglevel == 'allocation' or orglevel == 'project':
            return orglevel

        retval = {
                'name': orglevel.name,
                'level': orglevel.level,
                'export_to_xdmod': orglevel.export_to_xdmod,
           }
        if orglevel.parent is None:
            retval['parent'] = None
        else:
            retval['parent'] = orglevel.parent.name
        return retval

    def orglevels_to_dicts(self, orglevels):
        """Run orglevel_to_dict on a list of orglevels"""
        retval = []
        for orglevel in orglevels:
            tmp = self.orglevel_to_dict(orglevel)
            retval.append(tmp)
        return retval

    def dump_orglevel(self, orglevel):
        """For debugging: dumps an OrganizationLevel instance to stderr"""
        if orglevel == 'allocation' or orglevel == 'project':
            sys.stderr.write('[VERBOSE] orglevel={}\n'.format(orglevel))
            return

        name = orglevel.name
        level = orglevel.level
        xport = orglevel.export_to_xdmod
        sys.stderr.write('[VERBOSE] OrgLevel={}:{} (xport={})\n'.format(
            name, level, xport))
        return

    def dump_orglevels(self, orglevels):
        """For debugging: dumps a list of  OrganizationLevels to stderr"""
        for orglevel in orglevels:
            self.dump_orglevel(orglevel)
        return

    def do_xdmod_orglevel_hierarchy_list_test(self, varhash, 
            expected, testname='Unknown'):
        """Do a test of xdmod_orglevel_hierarchy_list() method.

        Expects a varhash giving desired xdmod settings (e.g. 
        XDMOD_MAX_HIERARCHY_TIERS, XDMOD_ALLOCATION/PROJECT_IN_HIERARCHY)
        and the expected output of the xdmod_orglevel_hierarchy_list.
        """
        self.set_and_cache_coldfront_config_variables(varhash)
        hlist = xdmod.xdmod_orglevel_hierarchy_list()

#        # For debugging
        if 'orglevel' in VERBOSE_TEST_OUTPUT:       
            sys.stderr.write('\n[VERBOSE] xdmod_orglevel_hierarchy_list ;'
                'for {} returned:\n---\n'.format(testname))
            self.dump_orglevels(hlist)
            sys.stderr.write('---\n')

        hdict = self.orglevels_to_dicts(hlist)
        self.restore_cached_coldfront_config_variables(varhash)
        self.assertEqual(hdict, expected)
        return

    def do_hierarchy_json_test(self, varhash, expected, testname='Unknown'):
        """Do a test of generate_xdmod_orglevel_hierarchy_setup() method.

        Expects a varhash giving desired xdmod settings (e.g. 
        XDMOD_MAX_HIERARCHY_TIERS, XDMOD_ALLOCATION/PROJECT_IN_HIERARCHY)
        and the expected output of the method
        """
        self.set_and_cache_coldfront_config_variables(varhash)
        got = xdmod.generate_xdmod_orglevel_hierarchy_setup()

        # For debugging
        if 'hier_json' in VERBOSE_TEST_OUTPUT:       
            sys.stderr.write('\n[VERBOSE] generate_xdmod_orglevel_hierarchy_setup '
                'for {} returned:\n---\n'.format(testname))
            sys.stderr.write('{}\n'.format(got))
            sys.stderr.write('---\n')

        self.restore_cached_coldfront_config_variables(varhash)
        self.assertEqual(got, expected)
        return

    def do_hierarchy_csv_test(self, varhash, expected, testname='Unknown'):
        """Do a test of generate_xdmod_org_hierarchy method.

        Expects a varhash giving desired xdmod settings (e.g. 
        XDMOD_MAX_HIERARCHY_TIERS, XDMOD_ALLOCATION/PROJECT_IN_HIERARCHY)
        and the expected output of the method
        """
        self.set_and_cache_coldfront_config_variables(varhash)
        got = xdmod.generate_xdmod_org_hierarchy()

        # For debugging
        if 'hier_csv' in VERBOSE_TEST_OUTPUT:       
            sys.stderr.write('\n[VERBOSE] generate_xdmod_org_hierarchy '
                'for {} returned:\n---\n'.format(testname))
            for x in got:
                sys.stderr.write('{}\n'.format(x))
            sys.stderr.write('---\n')

        self.restore_cached_coldfront_config_variables(varhash)
        self.assertEqual(got, expected)
        return

    def do_group2hierarchy_test(self, varhash, expected, testname='Unknown'):
        """Do a test of generate_xdmod_group_to_hierarchy method.

        Expects a varhash giving desired xdmod settings (e.g. 
        XDMOD_MAX_HIERARCHY_TIERS, XDMOD_ALLOCATION/PROJECT_IN_HIERARCHY)
        and the expected output of the method
        """
        self.set_and_cache_coldfront_config_variables(varhash)
        got = xdmod.generate_xdmod_group_to_hierarchy()

        # For debugging
        if 'group2hier' in VERBOSE_TEST_OUTPUT:       
            sys.stderr.write('\n[VERBOSE] generate_xdmod_org_hierarchy '
                'for {} returned:\n---\n'.format(testname))
            for x in got:
                sys.stderr.write('{}\n'.format(x))
            sys.stderr.write('---\n')

        self.restore_cached_coldfront_config_variables(varhash)
        self.assertEqual(got, expected)
        return

    def do_names_csv_user_test(self, varhash, expected, testname='Unknown'):
        """Do a test of generate_xdmod_names_for_users

        Expects a varhash giving desired xdmod settings (e.g. 
        XDMOD_MAX_HIERARCHY_TIERS, XDMOD_ALLOCATION/PROJECT_IN_HIERARCHY)
        and the expected output of the method
        """
        self.set_and_cache_coldfront_config_variables(varhash)
        got = xdmod.generate_xdmod_names_for_users()

        # For debugging
        if 'names_csv' in VERBOSE_TEST_OUTPUT:       
            sys.stderr.write('\n[VERBOSE] generate_xdmod_org_hierarchy '
                'for {} returned:\n---\n'.format(testname))
            for x in got:
                sys.stderr.write('{}\n'.format(x))
            sys.stderr.write('---\n')

        self.restore_cached_coldfront_config_variables(varhash)
        self.assertEqual(got, expected)
        return


    ########################################################################
    #                       Tests
    ########################################################################

    def test_xdmod_orglevel_hierarchy_list_noproj_noalloc_max3(self):
        """Test xdmod_orglevel_hierarchy_list: max levels=3, no proj/allocs.
        """
        testname = 'xdmod_orglevel_hierarchy_list_noproj_noalloc_max3'
        varhash = {
            'xdmod': {
                    'XDMOD_MAX_HIERARCHY_TIERS': 3,
                    'XDMOD_ALLOCATION_IN_HIERARCHY': False,
                    'XDMOD_PROJECT_IN_HIERARCHY': False,
                },
            }
        expected = [
                EXPECTED_DEPT_ORGLEV,
                EXPECTED_COLL_ORGLEV,
                EXPECTED_UNIV_ORGLEV,
            ]

        self.do_xdmod_orglevel_hierarchy_list_test(
                varhash, expected, testname)
        return

    def test_xdmod_orglevel_hierarchy_list_noproj_alloc_max3(self):
        """Test xdmod_orglevel_hierarchy_list: max levels=3, no proj, w allocs.
        """
        testname = 'xdmod_orglevel_hierarchy_list_noproj_alloc_max3'
        varhash = {
            'xdmod': {
                    'XDMOD_MAX_HIERARCHY_TIERS': 3,
                    'XDMOD_ALLOCATION_IN_HIERARCHY': True,
                    'XDMOD_PROJECT_IN_HIERARCHY': False,
                },
            }
        expected = [
                'allocation',
                EXPECTED_DEPT_ORGLEV,
                EXPECTED_COLL_ORGLEV,
            ]

        self.do_xdmod_orglevel_hierarchy_list_test(
                varhash, expected, testname)
        return

    def test_xdmod_orglevel_hierarchy_list_proj_alloc_max3(self):
        """Test xdmod_orglevel_hierarchy_list: max levels=3, w proj, allocs.
        """
        testname = 'xdmod_orglevel_hierarchy_list_proj_alloc_max3'
        varhash = {
            'xdmod': {
                    'XDMOD_MAX_HIERARCHY_TIERS': 3,
                    'XDMOD_ALLOCATION_IN_HIERARCHY': True,
                    'XDMOD_PROJECT_IN_HIERARCHY': True,
                },
            }
        expected = [
                'allocation',
                'project',
                EXPECTED_DEPT_ORGLEV,
            ]

        self.do_xdmod_orglevel_hierarchy_list_test(
                varhash, expected, testname)
        return

    def test_xdmod_orglevel_hierarchy_list_proj_noalloc_max3(self):
        """Test xdmod_orglevel_hierarchy_list: max levels=3, no alloc, w projs
        """
        testname = 'xdmod_orglevel_hierarchy_list_proj_noalloc_max3'
        varhash = {
            'xdmod': {
                    'XDMOD_MAX_HIERARCHY_TIERS': 3,
                    'XDMOD_ALLOCATION_IN_HIERARCHY': False,
                    'XDMOD_PROJECT_IN_HIERARCHY': True,
                },
            }
        expected = [
                'project',
                EXPECTED_DEPT_ORGLEV,
                EXPECTED_COLL_ORGLEV,
            ]

        self.do_xdmod_orglevel_hierarchy_list_test(
                varhash, expected, testname)
        return

    def test_xdmod_orglevel_hierarchy_list_noproj_noalloc_max5(self):
        """Test xdmod_orglevel_hierarchy_list: max levels=5, no proj/allocs.
        """
        testname = 'xdmod_orglevel_hierarchy_list_noproj_noalloc_max5'
        varhash = {
            'xdmod': {
                    'XDMOD_MAX_HIERARCHY_TIERS': 5,
                    'XDMOD_ALLOCATION_IN_HIERARCHY': False,
                    'XDMOD_PROJECT_IN_HIERARCHY': False,
                },
            }
        expected = [
                EXPECTED_DEPT_ORGLEV,
                EXPECTED_COLL_ORGLEV,
                EXPECTED_UNIV_ORGLEV,
            ]

        self.do_xdmod_orglevel_hierarchy_list_test(
                varhash, expected, testname)
        return

    def test_xdmod_orglevel_hierarchy_list_noproj_noalloc_max2(self):
        """Test xdmod_orglevel_hierarchy_list: max levels=2, no proj/allocs.
        """
        testname = 'xdmod_orglevel_hierarchy_list_noproj_noalloc_max2'
        varhash = {
            'xdmod': {
                    'XDMOD_MAX_HIERARCHY_TIERS': 2,
                    'XDMOD_ALLOCATION_IN_HIERARCHY': False,
                    'XDMOD_PROJECT_IN_HIERARCHY': False,
                },
            }
        expected = [
                EXPECTED_DEPT_ORGLEV,
                EXPECTED_COLL_ORGLEV,
            ]

        self.do_xdmod_orglevel_hierarchy_list_test(
                varhash, expected, testname)
        return

    def test_xdmod_orglevel_hierarchy_list_noproj_noalloc_max1(self):
        """Test xdmod_orglevel_hierarchy_list: max levels=1, no proj/allocs.
        """
        testname = 'xdmod_orglevel_hierarchy_list_noproj_noalloc_max1'
        varhash = {
            'xdmod': {
                    'XDMOD_MAX_HIERARCHY_TIERS': 1,
                    'XDMOD_ALLOCATION_IN_HIERARCHY': False,
                    'XDMOD_PROJECT_IN_HIERARCHY': False,
                },
            }
        expected = [
                EXPECTED_DEPT_ORGLEV,
            ]

        self.do_xdmod_orglevel_hierarchy_list_test(
                varhash, expected, testname)
        return

    def test_xdmod_orglevel_hierarchy_list_proj_noalloc_max5(self):
        """Test xdmod_orglevel_hierarchy_list: max levels=5, no allocs w proj.
        """
        testname = 'xdmod_orglevel_hierarchy_list_proj_noalloc_max5'
        varhash = {
            'xdmod': {
                    'XDMOD_MAX_HIERARCHY_TIERS': 5,
                    'XDMOD_ALLOCATION_IN_HIERARCHY': False,
                    'XDMOD_PROJECT_IN_HIERARCHY': True,
                },
            }
        expected = [
                'project',
                EXPECTED_DEPT_ORGLEV,
                EXPECTED_COLL_ORGLEV,
                EXPECTED_UNIV_ORGLEV,
            ]

        self.do_xdmod_orglevel_hierarchy_list_test(
                varhash, expected, testname)
        return

    def test_xdmod_orglevel_hierarchy_list_proj_alloc_max5(self):
        """Test xdmod_orglevel_hierarchy_list: max levels=5, w proj/allocs.
        """
        testname = 'xdmod_orglevel_hierarchy_list_proj_alloc_max5'
        varhash = {
            'xdmod': {
                    'XDMOD_MAX_HIERARCHY_TIERS': 5,
                    'XDMOD_ALLOCATION_IN_HIERARCHY': True,
                    'XDMOD_PROJECT_IN_HIERARCHY': True,
                },
            }
        expected = [
                'allocation',
                'project',
                EXPECTED_DEPT_ORGLEV,
                EXPECTED_COLL_ORGLEV,
                EXPECTED_UNIV_ORGLEV,
            ]

        self.do_xdmod_orglevel_hierarchy_list_test(
                varhash, expected, testname)
        return

    def test_xdmod_orglevel_hierarchy_list_noproj_alloc_max5(self):
        """Test xdmod_orglevel_hierarchy_list: max levels=5, no proj w allocs.
        """
        testname = 'xdmod_orglevel_hierarchy_list_noproj_alloc_max5'
        varhash = {
            'xdmod': {
                    'XDMOD_MAX_HIERARCHY_TIERS': 5,
                    'XDMOD_ALLOCATION_IN_HIERARCHY': True,
                    'XDMOD_PROJECT_IN_HIERARCHY': False,
                },
            }
        expected = [
                'allocation',
                EXPECTED_DEPT_ORGLEV,
                EXPECTED_COLL_ORGLEV,
                EXPECTED_UNIV_ORGLEV,
            ]

        self.do_xdmod_orglevel_hierarchy_list_test(
                varhash, expected, testname)
        return

    def test_hierarchy_json_noalloc_noproj(self):
        """Test generate_xdmod_orglevel_hierarchy_setup, no proj/alloc
        """
        testname = 'hierarchy_json_noalloc_noproj'
        varhash = {
            'xdmod': {
                    'XDMOD_ALLOCATION_IN_HIERARCHY': False,
                    'XDMOD_PROJECT_IN_HIERARCHY': False,
                },
            }
        expected = {
                'bottom_level_info': 'Department',
                'bottom_level_label': 'Department',
                'middle_level_info': 'College',
                'middle_level_label': 'College',
                'top_level_info': 'University',
                'top_level_label': 'University',
            }

        self.do_hierarchy_json_test(varhash, expected, testname)
        return

    def test_hierarchy_json_alloc_noproj(self):
        """Test generate_xdmod_orglevel_hierarchy_setup, no proj w alloc
        """
        testname = 'hierarchy_json_alloc_noproj'
        varhash = {
            'xdmod': {
                    'XDMOD_ALLOCATION_IN_HIERARCHY': True,
                    'XDMOD_PROJECT_IN_HIERARCHY': False,
                    'XDMOD_ALLOCATION_HIERARCHY_LABEL': 'Allocation',
                    'XDMOD_ALLOCATION_HIERARCHY_INFO': 'One or more Allocations',
                },
            }
        expected = {
                'bottom_level_info': 'One or more Allocations',
                'bottom_level_label': 'Allocation',
                'middle_level_info': 'Department',
                'middle_level_label': 'Department',
                'top_level_info': 'College',
                'top_level_label': 'College',
            }

        self.do_hierarchy_json_test(varhash, expected, testname)
        return

    def test_hierarchy_json_noalloc_proj(self):
        """Test generate_xdmod_orglevel_hierarchy_setup, no alloc w proj
        """
        testname = 'hierarchy_json_noalloc_proj'
        varhash = {
            'xdmod': {
                    'XDMOD_ALLOCATION_IN_HIERARCHY': False,
                    'XDMOD_PROJECT_IN_HIERARCHY': True,
                    'XDMOD_PROJECT_HIERARCHY_LABEL': 'Project',
                    'XDMOD_PROJECT_HIERARCHY_INFO': 'All Allocations in Project',
                },
            }
        expected = {
                'bottom_level_info': 'All Allocations in Project',
                'bottom_level_label': 'Project',
                'middle_level_info': 'Department',
                'middle_level_label': 'Department',
                'top_level_info': 'College',
                'top_level_label': 'College',
            }

        self.do_hierarchy_json_test(varhash, expected, testname)
        return

    def test_hierarchy_json_alloc_proj(self):
        """Test generate_xdmod_orglevel_hierarchy_setup, w proj/alloc
        """
        testname = 'hierarchy_json_alloc_proj'
        varhash = {
            'xdmod': {
                    'XDMOD_ALLOCATION_IN_HIERARCHY': True,
                    'XDMOD_PROJECT_IN_HIERARCHY': True,
                    'XDMOD_ALLOCATION_HIERARCHY_LABEL': 'Allocation',
                    'XDMOD_ALLOCATION_HIERARCHY_INFO': 'Allocations',
                    'XDMOD_PROJECT_HIERARCHY_LABEL': 'Project',
                    'XDMOD_PROJECT_HIERARCHY_INFO': 'Allocations in Project',
                },
            }
        expected = {
                'bottom_level_info': 'Allocations',
                'bottom_level_label': 'Allocation',
                'middle_level_info': 'Allocations in Project',
                'middle_level_label': 'Project',
                'top_level_info': 'Department',
                'top_level_label': 'Department',
            }

        self.do_hierarchy_json_test(varhash, expected, testname)
        return

    def test_hierarchy_csv_noproj_noalloc(self):
        """Test generate_xdmod_org_hierarchy: no proj/alloc
        """
        testname = 'hierarchy_csv_noproj_noalloc'
        varhash = {
            'xdmod': {
                    'XDMOD_MAX_HIERARCHY_TIERS': 3,
                    'XDMOD_ALLOCATION_IN_HIERARCHY': False,
                    'XDMOD_PROJECT_IN_HIERARCHY': False,
                },
            }
        expected = (EXPECTED_ORGLIST_UNIV +
            EXPECTED_ORGLIST_COLL +
            EXPECTED_ORGLIST_DEPT)

        self.do_hierarchy_csv_test(varhash, expected, testname)
        return

    def test_hierarchy_csv_proj_noalloc_defmode(self):
        """Test generate_xdmod_org_hierarchy: proj but no alloc
        """
        testname = 'hierarchy_csv_proj_noalloc_defmode'
        varhash = {
            'xdmod': {
                    'XDMOD_MAX_HIERARCHY_TIERS': 3,
                    'XDMOD_ALLOCATION_IN_HIERARCHY': False,
                    'XDMOD_PROJECT_IN_HIERARCHY': True,
                    'XDMOD_PROJECT_HIERARCHY_CODE_PREFIX': 'proj-',
                    'XDMOD_PROJECT_HIERARCHY_CODE_SUFFIX': '-prj',
                },
            'slurm': {
                    'SLURM_ACCOUNT_ATTRIBUTE_NAME': 'slurm_account_name',
                },
            }
        
        tmp_coll = [ (x[0], x[1], None) for x in EXPECTED_ORGLIST_COLL ]
        expected = (tmp_coll +
            EXPECTED_ORGLIST_DEPT +
            EXPECTED_ORGLIST_PROJ_NOALLOC_PI)

        self.do_hierarchy_csv_test(varhash, expected, testname)
        return

    def test_hierarchy_csv_proj_noalloc_pimode(self):
        """Test generate_xdmod_org_hierarchy: proj but no alloc, pimode
        """
        testname = 'hierarchy_csv_proj_noalloc_pimode'
        varhash = {
            'xdmod': {
                    'XDMOD_MAX_HIERARCHY_TIERS': 3,
                    'XDMOD_ALLOCATION_IN_HIERARCHY': False,
                    'XDMOD_PROJECT_IN_HIERARCHY': True,
                    'XDMOD_PROJECT_HIERARCHY_CODE_MODE': 'pi_username',
                    'XDMOD_PROJECT_HIERARCHY_CODE_PREFIX': 'proj-',
                    'XDMOD_PROJECT_HIERARCHY_CODE_SUFFIX': '-prj',
                },
            'slurm': {
                    'SLURM_ACCOUNT_ATTRIBUTE_NAME': 'slurm_account_name',
                },
            }
        
        tmp_coll = [ (x[0], x[1], None) for x in EXPECTED_ORGLIST_COLL ]
        expected = (tmp_coll +
            EXPECTED_ORGLIST_DEPT +
            EXPECTED_ORGLIST_PROJ_NOALLOC_PI)

        self.do_hierarchy_csv_test(varhash, expected, testname)
        return

    def test_hierarchy_csv_proj_noalloc_titlemode(self):
        """Test generate_xdmod_org_hierarchy: proj but no alloc, titlemode
        """
        testname = 'hierarchy_csv_proj_noalloc_titlemode'
        varhash = {
            'xdmod': {
                    'XDMOD_MAX_HIERARCHY_TIERS': 3,
                    'XDMOD_ALLOCATION_IN_HIERARCHY': False,
                    'XDMOD_PROJECT_IN_HIERARCHY': True,
                    'XDMOD_PROJECT_HIERARCHY_CODE_MODE': 'title',
                    'XDMOD_PROJECT_HIERARCHY_CODE_PREFIX': 'proj-',
                },
            'slurm': {
                    'SLURM_ACCOUNT_ATTRIBUTE_NAME': 'slurm_account_name',
                },
            }
        
        tmp_coll = [ (x[0], x[1], None) for x in EXPECTED_ORGLIST_COLL ]
        expected = (tmp_coll +
            EXPECTED_ORGLIST_DEPT +
            EXPECTED_ORGLIST_PROJ_NOALLOC_TITLE)

        self.do_hierarchy_csv_test(varhash, expected, testname)
        return

    def test_hierarchy_csv_proj_noalloc_pslurmmode(self):
        """Test generate_xdmod_org_hierarchy: proj but no alloc, +slurm mode
        """
        testname = 'hierarchy_csv_proj_noalloc_pslurmemode'
        varhash = {
            'xdmod': {
                    'XDMOD_MAX_HIERARCHY_TIERS': 3,
                    'XDMOD_ALLOCATION_IN_HIERARCHY': False,
                    'XDMOD_PROJECT_IN_HIERARCHY': True,
                    'XDMOD_PROJECT_HIERARCHY_CODE_MODE': '+slurm_account_name',
                    'XDMOD_PROJECT_HIERARCHY_CODE_PREFIX': 'proj-',
                },
            'slurm': {
                    'SLURM_ACCOUNT_ATTRIBUTE_NAME': 'slurm_account_name',
                },
            }
        
        tmp_coll = [ (x[0], x[1], None) for x in EXPECTED_ORGLIST_COLL ]
        expected = (tmp_coll +
            EXPECTED_ORGLIST_DEPT +
            EXPECTED_ORGLIST_PROJ_NOALLOC_PSLURM)

        self.do_hierarchy_csv_test(varhash, expected, testname)
        return

    def test_hierarchy_csv_proj_noalloc_mslurmmode(self):
        """Test generate_xdmod_org_hierarchy: proj but no alloc, -slurm mode
        """
        testname = 'hierarchy_csv_proj_noalloc_mslurmemode'
        varhash = {
            'xdmod': {
                    'XDMOD_MAX_HIERARCHY_TIERS': 3,
                    'XDMOD_ALLOCATION_IN_HIERARCHY': False,
                    'XDMOD_PROJECT_IN_HIERARCHY': True,
                    'XDMOD_PROJECT_HIERARCHY_CODE_MODE': '-slurm_account_name',
                    'XDMOD_PROJECT_HIERARCHY_CODE_PREFIX': 'proj-',
                },
            'slurm': {
                    'SLURM_ACCOUNT_ATTRIBUTE_NAME': 'slurm_account_name',
                },
            }
        
        tmp_coll = [ (x[0], x[1], None) for x in EXPECTED_ORGLIST_COLL ]
        expected = (tmp_coll +
            EXPECTED_ORGLIST_DEPT +
            EXPECTED_ORGLIST_PROJ_NOALLOC_MSLURM)

        self.do_hierarchy_csv_test(varhash, expected, testname)
        return

    def test_hierarchy_csv_proj_noalloc_attribmode(self):
        """Test generate_xdmod_org_hierarchy: proj but no alloc, attrib mode
        """
        testname = 'hierarchy_csv_proj_noalloc_attribmode'
        varhash = {
            'xdmod': {
                    'XDMOD_MAX_HIERARCHY_TIERS': 3,
                    'XDMOD_ALLOCATION_IN_HIERARCHY': False,
                    'XDMOD_PROJECT_IN_HIERARCHY': True,
                    'XDMOD_PROJECT_HIERARCHY_CODE_MODE': 'attribute',
                    'XDMOD_PROJECT_HIERARCHY_CODE_ATTRIBUTE_NAME': 'xdmod_project_code',
                    'XDMOD_PROJECT_HIERARCHY_CODE_PREFIX': 'proj-',
                    'XDMOD_PROJECT_HIERARCHY_CODE_SUFFIX': '-prj',
                },
            'slurm': {
                    'SLURM_ACCOUNT_ATTRIBUTE_NAME': 'slurm_account_name',
                },
            }
        
        tmp_coll = [ (x[0], x[1], None) for x in EXPECTED_ORGLIST_COLL ]
        expected = (tmp_coll +
            EXPECTED_ORGLIST_DEPT +
            EXPECTED_ORGLIST_PROJ_NOALLOC_ATTRIB)

        self.do_hierarchy_csv_test(varhash, expected, testname)
        return

    def test_hierarchy_csv_proj_noalloc_attribpimode(self):
        """Test generate_xdmod_org_hierarchy: proj but no alloc, attrib,pi mode
        """
        testname = 'hierarchy_csv_proj_noalloc_attribpimode'
        varhash = {
            'xdmod': {
                    'XDMOD_MAX_HIERARCHY_TIERS': 3,
                    'XDMOD_ALLOCATION_IN_HIERARCHY': False,
                    'XDMOD_PROJECT_IN_HIERARCHY': True,
                    'XDMOD_PROJECT_HIERARCHY_CODE_MODE': 'attribute,pi_username',
                    'XDMOD_PROJECT_HIERARCHY_CODE_ATTRIBUTE_NAME': 'xdmod_project_code',
                    'XDMOD_PROJECT_HIERARCHY_CODE_PREFIX': 'proj-',
                    'XDMOD_PROJECT_HIERARCHY_CODE_SUFFIX': '-prj',
                },
            'slurm': {
                    'SLURM_ACCOUNT_ATTRIBUTE_NAME': 'slurm_account_name',
                },
            }
        
        tmp_coll = [ (x[0], x[1], None) for x in EXPECTED_ORGLIST_COLL ]
        expected = (tmp_coll +
            EXPECTED_ORGLIST_DEPT +
            EXPECTED_ORGLIST_PROJ_NOALLOC_ATTRIB)

        self.do_hierarchy_csv_test(varhash, expected, testname)
        return

    def test_hierarchy_csv_proj_noalloc_attribslurmmode(self):
        """Test generate_xdmod_org_hierarchy: proj but no alloc, attrib,slurm mode
        """
        testname = 'hierarchy_csv_proj_noalloc_attribslurmmode'
        varhash = {
            'xdmod': {
                    'XDMOD_MAX_HIERARCHY_TIERS': 3,
                    'XDMOD_ALLOCATION_IN_HIERARCHY': False,
                    'XDMOD_PROJECT_IN_HIERARCHY': True,
                    'XDMOD_PROJECT_HIERARCHY_CODE_MODE': 'attribute,slurm_account_name',
                    'XDMOD_PROJECT_HIERARCHY_CODE_ATTRIBUTE_NAME': 'xdmod_project_code',
                    'XDMOD_PROJECT_HIERARCHY_CODE_PREFIX': 'proj-',
                },
            'slurm': {
                    'SLURM_ACCOUNT_ATTRIBUTE_NAME': 'slurm_account_name',
                },
            }
        
        tmp_coll = [ (x[0], x[1], None) for x in EXPECTED_ORGLIST_COLL ]
        expected = (tmp_coll +
            EXPECTED_ORGLIST_DEPT +
            EXPECTED_ORGLIST_PROJ_NOALLOC_ATTRIB_SLURM)

        self.do_hierarchy_csv_test(varhash, expected, testname)
        return

    def test_hierarchy_csv_noproj_alloc(self):
        """Test generate_xdmod_org_hierarchy: alloc but no proj
        """
        testname = 'hierarchy_csv_noproj_alloc'
        varhash = {
            'xdmod': {
                    'XDMOD_MAX_HIERARCHY_TIERS': 3,
                    'XDMOD_ALLOCATION_IN_HIERARCHY': True,
                    'XDMOD_PROJECT_IN_HIERARCHY': False,
                    'XDMOD_ALLOCATION_HIERARCHY_CODE_ATTRIBUTE_NAME': 'xdmod_allocation_code',
                    'XDMOD_ALLOCATION_HIERARCHY_NAME_ATTRIBUTE_NAME': 'xdmod_allocation_name',
                    'XDMOD_ALLOCATION_HIERARCHY_CODE_PREFIX': 'alloc-',
                    'XDMOD_ALLOCATION_HIERARCHY_CODE_SUFFIX': '-suffix',
                },
            'slurm': {
                    'SLURM_ACCOUNT_ATTRIBUTE_NAME': 'slurm_account_name',
                },
            }
        
        tmp_coll = [ (x[0], x[1], None) for x in EXPECTED_ORGLIST_COLL ]
        expected = (tmp_coll +
            EXPECTED_ORGLIST_DEPT +
            EXPECTED_ORGLIST_NOPROJ_ALLOC)

        self.do_hierarchy_csv_test(varhash, expected, testname)
        return

    def test_hierarchy_csv_proj_alloc(self):
        """Test generate_xdmod_org_hierarchy: alloc and proj
        """
        testname = 'hierarchy_csv_proj_alloc'
        varhash = {
            'xdmod': {
                    'XDMOD_MAX_HIERARCHY_TIERS': 3,
                    'XDMOD_ALLOCATION_IN_HIERARCHY': True,
                    'XDMOD_PROJECT_IN_HIERARCHY': True,
                    'XDMOD_ALLOCATION_HIERARCHY_CODE_ATTRIBUTE_NAME': 'xdmod_allocation_code',
                    'XDMOD_ALLOCATION_HIERARCHY_NAME_ATTRIBUTE_NAME': 'xdmod_allocation_name',
                    'XDMOD_ALLOCATION_HIERARCHY_CODE_PREFIX': 'alloc-',
                    'XDMOD_ALLOCATION_HIERARCHY_CODE_SUFFIX': '-suffix',
                    'XDMOD_PROJECT_HIERARCHY_CODE_MODE': 'attribute,slurm_account_name',
                    'XDMOD_PROJECT_HIERARCHY_CODE_ATTRIBUTE_NAME': 'xdmod_project_code',
                    'XDMOD_PROJECT_HIERARCHY_CODE_PREFIX': 'proj-',
                },
            'slurm': {
                    'SLURM_ACCOUNT_ATTRIBUTE_NAME': 'slurm_account_name',
                },
            }
        
        tmp_dept = [ (x[0], x[1], None) for x in EXPECTED_ORGLIST_DEPT ]
        expected = (tmp_dept +
            EXPECTED_ORGLIST_PROJ_NOALLOC_ATTRIB_SLURM +
            EXPECTED_ORGLIST_PROJ_ALLOC)

        self.do_hierarchy_csv_test(varhash, expected, testname)
        return

    def test_hierarchy_csv_proj_noalloc_dropcoll(self):
        """Test generate_xdmod_org_hierarchy: proj and noalloc, w/out coll

        We hack so colleges are no longer exported2xdmod
        """
        testname = 'hierarchy_csv_proj_noalloc_dropcoll'
        varhash = {
            'xdmod': {
                    'XDMOD_MAX_HIERARCHY_TIERS': 3,
                    'XDMOD_ALLOCATION_IN_HIERARCHY': False,
                    'XDMOD_PROJECT_IN_HIERARCHY': True,
                    'XDMOD_PROJECT_HIERARCHY_CODE_MODE': 'attribute,slurm_account_name',
                    'XDMOD_PROJECT_HIERARCHY_CODE_ATTRIBUTE_NAME': 'xdmod_project_code',
                    'XDMOD_PROJECT_HIERARCHY_CODE_PREFIX': 'proj-',
                },
            'slurm': {
                    'SLURM_ACCOUNT_ATTRIBUTE_NAME': 'slurm_account_name',
                },
            }

        # Hack: temporily unexport_to_xdmod at the college level
        coll = OrganizationLevel.objects.get(name='College')
        cached_export = coll.export_to_xdmod
        coll.export_to_xdmod = False
        coll.save()
        
        # To change parent in dept from College to Univ, just drop everything after the 
        # first hyphen ('-')
        tmp_dept = [ (x[0], x[1], x[2].split('-',1)[0] ) for x in EXPECTED_ORGLIST_DEPT ]
        expected = (
            EXPECTED_ORGLIST_UNIV +
            tmp_dept +
            EXPECTED_ORGLIST_PROJ_NOALLOC_ATTRIB_SLURM)

        try:
            self.do_hierarchy_csv_test(varhash, expected, testname)
        finally:
            # Restore export_to_xdmod at the college level
            coll.export_to_xdmod = cached_export
            coll.save()

        return

    def test_hierarchy_csv_proj_alloc_bad_slurm_acct(self):
        """Test generate_xdmod_org_hierarchy: alloc and proj with bogus SLURM_ACCOUNT_ATTRIB_NAME

        This checks we are not hard coded slurm_account_name
        """
        testname = 'hierarchy_csv_proj_alloc_bad_slurm_acct'
        varhash = {
            'xdmod': {
                    'XDMOD_MAX_HIERARCHY_TIERS': 3,
                    'XDMOD_ALLOCATION_IN_HIERARCHY': True,
                    'XDMOD_PROJECT_IN_HIERARCHY': True,
                    'XDMOD_ALLOCATION_HIERARCHY_CODE_ATTRIBUTE_NAME': 'xdmod_allocation_code',
                    'XDMOD_ALLOCATION_HIERARCHY_NAME_ATTRIBUTE_NAME': 'xdmod_allocation_name',
                    'XDMOD_ALLOCATION_HIERARCHY_CODE_PREFIX': 'alloc-',
                    'XDMOD_ALLOCATION_HIERARCHY_CODE_SUFFIX': '-suffix',
                    'XDMOD_PROJECT_HIERARCHY_CODE_MODE': 'attribute,slurm_account_name',
                    'XDMOD_PROJECT_HIERARCHY_CODE_ATTRIBUTE_NAME': 'xdmod_project_code',
                    'XDMOD_PROJECT_HIERARCHY_CODE_PREFIX': 'proj-',
                },
            'slurm': {
                    'SLURM_ACCOUNT_ATTRIBUTE_NAME': 'slurm_account_nameXXY',
                },
            }
        
        tmp_dept = [ (x[0], x[1], None) for x in EXPECTED_ORGLIST_DEPT ]
        expected = (tmp_dept)

        self.do_hierarchy_csv_test(varhash, expected, testname)
        return

    def test_group2hierarchy_dept(self):
        """Test generate_xdmod_group_to_hierarchy, noalloc, noproj
        """
        testname = 'group2hierarchy_dept'
        varhash = {
            'xdmod': {
                    'XDMOD_MAX_HIERARCHY_TIERS': 3,
                    'XDMOD_ALLOCATION_IN_HIERARCHY': False,
                    'XDMOD_PROJECT_IN_HIERARCHY': False,
                },
            'slurm': {
                    'SLURM_ACCOUNT_ATTRIBUTE_NAME': 'slurm_account_name',
                },
            }
        
        expected = EXPECTED_G2HIER_DEPT
        self.do_group2hierarchy_test(varhash, expected, testname)
        return

    def test_group2hierarchy_coll(self):
        """Test generate_xdmod_group_to_hierarchy, noalloc, noproj and unexporting dept
        """
        testname = 'group2hierarchy_coll'
        varhash = {
            'xdmod': {
                    'XDMOD_MAX_HIERARCHY_TIERS': 3,
                    'XDMOD_ALLOCATION_IN_HIERARCHY': False,
                    'XDMOD_PROJECT_IN_HIERARCHY': False,
                },
            'slurm': {
                    'SLURM_ACCOUNT_ATTRIBUTE_NAME': 'slurm_account_name',
                },
            }
        
        # Hack: temporily unexport_to_xdmod at the dept level
        dept = OrganizationLevel.objects.get(name='Department')
        cached_export = dept.export_to_xdmod
        dept.export_to_xdmod = False
        dept.save()
        
        tmp = [ (x[0], x[1].rsplit('-',1)[0]) for x in EXPECTED_G2HIER_DEPT ]
        expected = tmp
        try:
            self.do_group2hierarchy_test(varhash, expected, testname)
        finally:
            # Restore export_to_xdmod at the dept level
            dept.export_to_xdmod = cached_export
            dept.save()

        return

    def test_group2hierarchy_proj(self):
        """Test generate_xdmod_group_to_hierarchy, noalloc, proj
        """
        testname = 'group2hierarchy_proj'
        varhash = {
            'xdmod': {
                    'XDMOD_MAX_HIERARCHY_TIERS': 3,
                    'XDMOD_ALLOCATION_IN_HIERARCHY': False,
                    'XDMOD_PROJECT_IN_HIERARCHY': True,
                    'XDMOD_PROJECT_HIERARCHY_CODE_MODE': 'attribute,slurm_account_name',
                    'XDMOD_PROJECT_HIERARCHY_CODE_ATTRIBUTE_NAME': 'xdmod_project_code',
                    'XDMOD_PROJECT_HIERARCHY_CODE_PREFIX': 'proj-',
                },
            'slurm': {
                    'SLURM_ACCOUNT_ATTRIBUTE_NAME': 'slurm_account_name',
                },
            }
        
        expected = EXPECTED_G2HIER_PROJ
        self.do_group2hierarchy_test(varhash, expected, testname)
        return

    def test_group2hierarchy_alloc(self):
        """Test generate_xdmod_group_to_hierarchy, alloc, noproj
        """
        testname = 'group2hierarchy_alloc'
        varhash = {
            'xdmod': {
                    'XDMOD_MAX_HIERARCHY_TIERS': 3,
                    'XDMOD_ALLOCATION_IN_HIERARCHY': True,
                    'XDMOD_PROJECT_IN_HIERARCHY': False,
                    'XDMOD_ALLOCATION_HIERARCHY_CODE_ATTRIBUTE_NAME': 'xdmod_allocation_code',
                    'XDMOD_ALLOCATION_HIERARCHY_NAME_ATTRIBUTE_NAME': 'xdmod_allocation_name',
                    'XDMOD_ALLOCATION_HIERARCHY_CODE_PREFIX': 'alloc-',
                    'XDMOD_ALLOCATION_HIERARCHY_CODE_SUFFIX': '-suffix',
                },
            'slurm': {
                    'SLURM_ACCOUNT_ATTRIBUTE_NAME': 'slurm_account_name',
                },
            }
        
        expected = EXPECTED_G2HIER_ALLOC
        self.do_group2hierarchy_test(varhash, expected, testname)
        return

    def test_group2hierarchy_alloc_proj(self):
        """Test generate_xdmod_group_to_hierarchy, alloc, proj
        """
        testname = 'group2hierarchy_alloc_proj'
        varhash = {
            'xdmod': {
                    'XDMOD_MAX_HIERARCHY_TIERS': 3,
                    'XDMOD_ALLOCATION_IN_HIERARCHY': True,
                    'XDMOD_PROJECT_IN_HIERARCHY': True,
                    'XDMOD_ALLOCATION_HIERARCHY_CODE_ATTRIBUTE_NAME': 'xdmod_allocation_code',
                    'XDMOD_ALLOCATION_HIERARCHY_NAME_ATTRIBUTE_NAME': 'xdmod_allocation_name',
                    'XDMOD_ALLOCATION_HIERARCHY_CODE_PREFIX': 'alloc-',
                    'XDMOD_ALLOCATION_HIERARCHY_CODE_SUFFIX': '-suffix',
                    'XDMOD_PROJECT_HIERARCHY_CODE_MODE': 'attribute,slurm_account_name',
                    'XDMOD_PROJECT_HIERARCHY_CODE_ATTRIBUTE_NAME': 'xdmod_project_code',
                    'XDMOD_PROJECT_HIERARCHY_CODE_PREFIX': 'proj-',
                },
            'slurm': {
                    'SLURM_ACCOUNT_ATTRIBUTE_NAME': 'slurm_account_name',
                },
            }
        
        expected = EXPECTED_G2HIER_ALLOC
        self.do_group2hierarchy_test(varhash, expected, testname)
        return

    def test_names_csv_users(self):
        """Test generate_xdmod_names_for_users using defaults
        """
        testname = 'names_csv_users'
        varhash = {
            'xdmod': {
                    'XDMOD_NAMES_CSV_USER_FNAME_FORMAT': None,
                    'XDMOD_NAMES_CSV_USER_LNAME_FORMAT': None,
                },
            }
        
        expected = EXPECTED_NAMES_CSV_USER_DEFAULT
        self.do_names_csv_user_test(varhash, expected, testname)
        return

    def test_names_csv_users_custom1(self):
        """Test generate_xdmod_names_for_users using custom settings1
        """
        testname = 'names_csv_users'
        varhash = {
            'xdmod': {
                    'XDMOD_NAMES_CSV_USER_FNAME_FORMAT': '',
                    'XDMOD_NAMES_CSV_USER_LNAME_FORMAT': '{fname} {lname} ({email})',
                },
            }
        
        expected = EXPECTED_NAMES_CSV_USER_CUSTOM1
        self.do_names_csv_user_test(varhash, expected, testname)
        return

