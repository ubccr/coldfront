# Script to test OrganizationLevel, Organization methods
# including:
#   validate_orglevel_hierarchy
#   the integrity checks in clean(), etc.
#   the add_organization_level and delete_organization_level helper methods
#   validate_organization_hierarchy

import sys

from django.core.exceptions import ValidationError 
from django.db.models import ProtectedError
from django.test import TestCase

from coldfront.core.organization.models import (
        OrganizationLevel,
        Organization,
        )

VERBOSE_TESTS = set()
#VERBOSE_TESTS.add('orglevel_exceptions')
#VERBOSE_TESTS.add('org_exceptions')

EXPECTED_BASE_ORGLEVEL_HIERARCHY=[
    {   'name': 'University',
        'level': 40,
        'parent': None,
        'export_to_xdmod': True,
    },
    {   'name': 'College',
        'level': 30,
        'parent': 'University',
        'export_to_xdmod': True,

    },
    {   'name': 'Department',
        'level': 20,
        'parent': 'College',
        'export_to_xdmod': True,
    },
]

NEW_ORGLEVEL_LEAF={
        'name': 'ResearchGroup',
        'level': 10,
        'parent': 'Department',
        'export_to_xdmod': True,
    }

NEW_ORGLEVEL_BADLEAF1={
        'name': 'ResearchGroup',
        'level': 25,
        'parent': 'Department',
        'export_to_xdmod': True,
    }

NEW_ORGLEVEL_ROOT={
        'name': 'Country',
        'level': 50,
        'parent': None,
        'export_to_xdmod': True,
    }

NEW_ORGLEVEL_MIDDLE={
        'name': 'Campus',
        'level': 35,
        'parent': 'University',
        'export_to_xdmod': True,
    }

EXPECTED_BASE_ORGS= [
        {   'fullcode': 'UMB',
            'orglevel': 'University',
            'code': 'UMB',
            'shortname': 'UMD Baltimore',
            'longname': 'University of Maryland, Baltimore',
            'is_selectable_for_project': False,
            'is_selectable_for_user': False,
            'parent': None,
        },
        {   'fullcode': 'UMD',
            'orglevel': 'University',
            'code': 'UMD',
            'shortname': 'UMCP',
            'longname': 'University of Maryland',
            'is_selectable_for_project': False,
            'is_selectable_for_user': False,
            'parent': None,
        },
        {   'fullcode': 'Unknown',
            'orglevel': 'University',
            'code': 'Unknown',
            'shortname': 'Unknown',
            'longname': 'Container for Unknown organizations', 
            'is_selectable_for_project': False,
            'is_selectable_for_user': False,
            'parent': None,
        },
        {   'fullcode': 'UMD-CMNS',
            'orglevel': 'College',
            'code': 'CMNS',
            'shortname': 'CMNS',
            'longname': 'College of Computer, Mathematical, and Natural Sciences',
            'is_selectable_for_project': False,
            'is_selectable_for_user': False,
            'parent': 'UMD',
        },
        {   'fullcode': 'UMD-ENGR',
            'orglevel': 'College',
            'code': 'ENGR',
            'shortname': 'Engineering',
            'longname': 'School of Engineering',
            'is_selectable_for_project': False,
            'is_selectable_for_user': False,
            'parent': 'UMD',
        },
        {   'fullcode': 'UMB-SoD',
            'orglevel': 'College',
            'code': 'SoD',
            'shortname': 'Dentistry',
            'longname': 'School of Dentistry',
            'is_selectable_for_project': False,
            'is_selectable_for_user': False,
            'parent': 'UMB',
        },
        {   'fullcode': 'UMB-SoM',
            'orglevel': 'College',
            'code': 'SoM',
            'shortname': 'Medicine',
            'longname': 'School of Medicine',
            'is_selectable_for_project': False,
            'is_selectable_for_user': False,
            'parent': 'UMB',
        },
        {   'fullcode': 'UMD-CMNS-ASTR',
            'orglevel': 'Department',
            'code': 'ASTR',
            'shortname': 'Astronomy',
            'longname': 'Astronomy Department',
            'is_selectable_for_project': True,
            'is_selectable_for_user': True,
            'parent': 'UMD-CMNS',
        },
        {   'fullcode': 'UMD-ENGR-ENAE',
            'orglevel': 'Department',
            'code': 'ENAE',
            'shortname': 'Aeronautical Eng',
            'longname': 'Dept of Aeronautical Engineering',
            'is_selectable_for_project': True,
            'is_selectable_for_user': True,
            'parent': 'UMD-ENGR',
        },
        {   'fullcode': 'UMD-ENGR-ENMA',
            'orglevel': 'Department',
            'code': 'ENMA',
            'shortname': 'Materials Eng',
            'longname': 'Dept of Materials Engineering',
            'is_selectable_for_project': True,
            'is_selectable_for_user': True,
            'parent': 'UMD-ENGR',
        },
        {   'fullcode': 'UMB-SoD-NeuPain',
            'orglevel': 'Department',
            'code': 'NeuPain',
            'shortname': 'Neural and Pain',
            'longname': 'Department of Neural and Pain Sciences',
            'is_selectable_for_project': True,
            'is_selectable_for_user': True,
            'parent': 'UMB-SoD',
        },
        {   'fullcode': 'UMD-CMNS-PHYS',
            'orglevel': 'Department',
            'code': 'PHYS',
            'shortname': 'Physics',
            'longname': 'Physics Department',
            'is_selectable_for_project': True,
            'is_selectable_for_user': True,
            'parent': 'UMD-CMNS',
        },
        {   'fullcode': 'UMB-SoD-Perio',
            'orglevel': 'Department',
            'code': 'Perio',
            'shortname': 'Periodontics',
            'longname': 'Division of Periodontics',
            'is_selectable_for_project': True,
            'is_selectable_for_user': True,
            'parent': 'UMB-SoD',
        },
        {   'fullcode': 'UMB-SoM-Psych',
            'orglevel': 'Department',
            'code': 'Psych',
            'shortname': 'Psychiatry',
            'longname': 'Psychiatry Department',
            'is_selectable_for_project': True,
            'is_selectable_for_user': True,
            'parent': 'UMB-SoM',
        },
        {   'fullcode': 'UMB-SoM-Surg',
            'orglevel': 'Department',
            'code': 'Surg',
            'shortname': 'Surgery',
            'longname': 'Surgery Department',
            'is_selectable_for_project': True,
            'is_selectable_for_user': True,
            'parent': 'UMB-SoM',
        },
    ]

NEW_ORGS_CAMPUS = [
        {   'fullcode': 'UMD-placeholderCMNS',
            'orglevel': 'Campus',
            'code': 'placeholderCMNS',
            'shortname': 'placeholderCMNS',
            'longname': 'placeholderCollege of Computer, Mathematical, and Natural Sciences',
            'is_selectable_for_project': True,
            'is_selectable_for_user': True,
            'parent': 'UMD',
        },
        {   'fullcode': 'UMD-placeholderENGR',
            'orglevel': 'Campus',
            'code': 'placeholderENGR',
            'shortname': 'placeholderEngineering',
            'longname': 'placeholderSchool of Engineering',
            'is_selectable_for_project': True,
            'is_selectable_for_user': True,
            'parent': 'UMD',
        },
        {   'fullcode': 'UMB-placeholderSoD',
            'orglevel': 'Campus',
            'code': 'placeholderSoD',
            'shortname': 'placeholderDentistry',
            'longname': 'placeholderSchool of Dentistry',
            'is_selectable_for_project': True,
            'is_selectable_for_user': True,
            'parent': 'UMB',
        },
        {   'fullcode': 'UMB-placeholderSoM',
            'orglevel': 'Campus',
            'code': 'placeholderSoM',
            'shortname': 'placeholderMedicine',
            'longname': 'placeholderSchool of Medicine',
            'is_selectable_for_project': True,
            'is_selectable_for_user': True,
            'parent': 'UMB',
        },
    ]

NEW_BAD_ORG1 = {   
        'fullcode': 'UMD-BAD1',
        'orglevel': 'Department',
        'code': 'BAD1',
        'shortname': 'Test skip College',
        'longname': 'Test skip College',
        'is_selectable_for_project': True,
        'is_selectable_for_user': True,
        'parent': 'UMD',
        }

class OrganizationLevelTest(TestCase):
    fixtures = ['organization_test_data.json']

    # Helper functions
    def orglevel_to_dict(self, orglevel):
        """Convert an OrgLevel to a dict"""
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
        name = orglevel.name
        level = orglevel.level
        parent = orglevel.parent
        pname = '<None>'
        if parent is not None:
            pname = parent.name
        xport = orglevel.export_to_xdmod
        sys.stderr.write('[DEBUG] OrgLevel={}:{} [parent={}] (xport={})\n'.format(
            name, level, pname, xport))
        return

    def dump_orglevels(self, orglevels):
        """For debugging: dumps a list of  OrganizationLevels to stderr"""
        for orglevel in orglevels:
            self.dump_orglevel(orglevel)
        return

    def org_to_dict(self, org):
        """Convert an Organization to a dict"""
        retval = {
                'fullcode': org.fullcode(),
                'orglevel': org.organization_level.name,
                'code': org.code,
                'shortname': org.shortname,
                'longname': org.longname,
                'is_selectable_for_user': org.is_selectable_for_user,
                'is_selectable_for_project': org.is_selectable_for_project,
           }
        if org.parent is None:
            retval['parent'] = None
        else:
            retval['parent'] = org.parent.fullcode()
        return retval

    def orgs_to_dicts(self, orgs=None):
        """Run orglevel_to_dict on a list of orglevels"""
        if orgs is None:
            orgs = Organization.objects.all()
        retval = []
        for org in orgs:
            tmp = self.org_to_dict(org)
            retval.append(tmp)
        return retval

    def dump_org(self, org):
        """For debugging: dumps an Organization instance to stderr"""
        fullcode = org.fullcode()
        short = org.shortname
        level = org.organization_level.name
        parent = org.parent
        pname = '<None>'
        if parent is not None:
            pname = parent.fullcode()
        sel_by_user = org.is_selectable_for_user
        sel_by_proj = org.is_selectable_for_project
        sys.stderr.write('[DEBUG] Org {}:{} level={} [parent={}] '
            '(selectable for user={}/proj={})\n'.format(
                fullcode, short, level, pname, sel_by_user,
                sel_by_proj))
        return

    def dump_orgs(self, orgs=None):
        """For debugging: dumps a list of  Organizations to stderr"""
        if orgs is None:
            orgs = Organization.objects.all()
        for org in orgs:
            self.dump_org(org)
        return

    ########################################################################
    #                       Tests
    ########################################################################

    def test_orglevel_validate_succeeds(self):
        """Test that validate_orglevel_hierarchy succeeds"""
        try:
            OrganizationLevel.validate_orglevel_hierarchy()
        except Exception as exc:
            self.fail('validate_orglevel_hierarchy raised exception: {}'.format(
                exc))
        return

    def test_orglevel_hierarchy_list(self):
        """Test that we get our expected orglevel hierarchy list"""
        hlist = OrganizationLevel.generate_orglevel_hierarchy_list()
        got = self.orglevels_to_dicts(hlist)
        expected = list(EXPECTED_BASE_ORGLEVEL_HIERARCHY)
        self.assertEqual(got, expected)
        return

    def test_org_validate_succeeds(self):
        """Test that validate_organization_hierarchy succeeds"""
        try:
            Organization.validate_organization_hierarchy(
                        only_leaves_are_selectable_for_project=True,
                        only_leaves_are_selectable_for_user=True,
                    )
        except Exception as exc:
            self.fail('validate_organization_hierarchy raised exception: {}'.format(
                exc))
        return

    def test_org_list(self):
        """Test that we get our expected organization list"""
        got = self.orgs_to_dicts()
        expected = list(EXPECTED_BASE_ORGS)
        self.assertEqual(got, expected)
        return

    def test_orglevel_add_delete_leaf_tier(self):
        """Test that we can successfully add and delete a leaf orglevel"""

        parent_oname = NEW_ORGLEVEL_LEAF['parent']
        parent_olev = OrganizationLevel.objects.get(name=parent_oname)
        new_args = dict(NEW_ORGLEVEL_LEAF)
        del new_args['parent']
        new_args['parent'] = parent_olev

        try:
            # Add OrgLevel
            newolev = OrganizationLevel.objects.create(**new_args)
        except Exception as exc:
            self.fail('exception raised on adding new leaf OrgLevel: {}'.format(
                exc))

        # Make sure OrgLevel hierarchy is correct
        hlist = OrganizationLevel.generate_orglevel_hierarchy_list()
        got = self.orglevels_to_dicts(hlist)
        expected = list(EXPECTED_BASE_ORGLEVEL_HIERARCHY)
        expected.append(NEW_ORGLEVEL_LEAF)
        self.assertEqual(got, expected)

        # Make sure Organization hierarchy is correct

        # We *should* have an issue is validate with only_leaves_are_selectable,
        # as our former leaves are no longer leaves
        with self.assertRaises(ValidationError) as cm:
            Organization.validate_organization_hierarchy(
                    only_leaves_are_selectable_for_project=True,
                    only_leaves_are_selectable_for_user=True,
                )
        # We should not have exception without only_leaves_are_selectable
        try:
            Organization.validate_organization_hierarchy()
        except Exception as exc:
            self.fail('exception raised on validate_organization_hier w/ou only_leaves_are_sel')

        got = self.orgs_to_dicts()
        expected = list(EXPECTED_BASE_ORGS)
        self.assertEqual(got, expected)

        try:
            # Delete OrgLevel
            newolev.delete()
        except Exception as exc:
            self.fail('exception raised on deleting new leaf OrgLevel: {}'.format(
                exc))

        # Make sure OrgLevel hierarchy is correct
        hlist = OrganizationLevel.generate_orglevel_hierarchy_list()
        got = self.orglevels_to_dicts(hlist)
        expected = list(EXPECTED_BASE_ORGLEVEL_HIERARCHY)
        self.assertEqual(got, expected)

        return

    def test_orglevel_dont_naive_add_root_tier(self):
        """Test that we cannot naively add a root tier"""
        # Add a root OrgLevel tier, we expect to fail
        testname = 'orglevel_dont_naive_add_root_tier'
        new_args = dict(NEW_ORGLEVEL_ROOT)
        newolev = None
        with self.assertRaises(ValidationError) as cm:
            newolev = OrganizationLevel.objects.create(**new_args)

        if newolev is not None:
            # Cleanup in case did not raise exception
            newolev.delete()

        if 'orglevel_exceptions' in VERBOSE_TESTS:
            exc = cm.exception
            sys.stderr.write('[DEBUG] {}: got exc={}: {}\n'.format(
                testname, type(exc), exc))

        return

    def test_orglevel_dont_naive_delete_root_tier(self):
        """Test that we cannot naively delete the root tier"""

        hlist = OrganizationLevel.generate_orglevel_hierarchy_list()
        oldroot = hlist[0]
        with self.assertRaises(ProtectedError) as cm:
            oldroot.delete()

        exc = cm.exception
        if not exc:
            sys.stderr.write(
                    '******************************\n'
                    '[FATAL] Deleted root orglevel tier\n'
                    'Subsequent tests likely to fail\n'
                    '******************************\n'
                    )
        return

    def test_orglevel_dont_naive_delete_middle_tier(self):
        """Test that we cannot naively delete the middle tier"""

        hlist = OrganizationLevel.generate_orglevel_hierarchy_list()
        middle = hlist[1]
        with self.assertRaises(ProtectedError) as cm:
            middle.delete()

        exc = cm.exception
        if not exc:
            sys.stderr.write(
                    '******************************\n'
                    '[FATAL] Deleted middle orglevel tier\n'
                    'Subsequent tests likely to fail\n'
                    '******************************\n'
                    )
        return

    def test_orglevel_dont_naive_delete_leaf_tier(self):
        """Test that we cannot naively delete the leaf tier"""

        hlist = OrganizationLevel.generate_orglevel_hierarchy_list()
        leaf = hlist[-1]
        with self.assertRaises(ProtectedError) as cm:
            leaf.delete()

        exc = cm.exception
        if not exc:
            sys.stderr.write(
                    '******************************\n'
                    '[FATAL] Deleted leaf orglevel tier\n'
                    'Subsequent tests likely to fail\n'
                    '******************************\n'
                    )
        return

    def test_orglevel_dont_naive_add_middle_tier(self):
        """Test that we cannot naively add a middle tier"""
        testname = 'orglevel_dont_naive_add_middle_tier'
        # Add a middle OrgLevel tier, we expect to fail
        new_args = dict(NEW_ORGLEVEL_MIDDLE)
        parent_oname = new_args['parent']
        del new_args['parent']

        parent_olev = OrganizationLevel.objects.get(name=parent_oname)
        new_args['parent'] = parent_olev
        newolev = None
        with self.assertRaises(ValidationError) as cm:
            newolev = OrganizationLevel.objects.create(**new_args)

        if newolev is not None:
            # Cleanup in case did not raise exception
            newolev.delete()

        if 'orglevel_exceptions' in VERBOSE_TESTS:
            exc = cm.exception
            sys.stderr.write('[DEBUG] {}: got exc={}: {}\n'.format(
                testname, type(exc), exc))
        return

    def test_orglevel_dont_naive_add_middle_tier2(self):
        """Test that we cannot naively add a middle tier even when checks disabled"""
        testname = 'orglevel_dont_naive_add_middle_tier2'
        new_args = dict(NEW_ORGLEVEL_MIDDLE)
        parent_oname = new_args['parent']
        del new_args['parent']
        parent_olev = OrganizationLevel.objects.get(name=parent_oname)
        new_args['parent'] = parent_olev
        newolev = None

        # Force the addition of an invalid root tier
        OrganizationLevel.disable_validation_checks(True)
        with self.assertRaises(ValidationError) as cm:
            newolev = OrganizationLevel.objects.create(**new_args)
        OrganizationLevel.disable_validation_checks(False)

        # Cleanup
        if newolev:
            OrganizationLevel.disable_validation_checks(True)
            newolev.delete()
            OrganizationLevel.disable_validation_checks(False)

        if 'orglevel_exceptions' in VERBOSE_TESTS:
            exc = cm.exception
            sys.stderr.write('[DEBUG] {}: got exc={}: {}\n'.format(
                testname, type(exc), exc))
        return

    def test_orglevel_dont_naive_add_badleaf1_tier(self):
        """Test that we cannot naively add a bad leaf tier (1)"""
        testname = 'orglevel_dont_naive_adD_badleaf1_tier'
        # Add a bad leaf1 OrgLevel tier, we expect to fail
        new_args = dict(NEW_ORGLEVEL_BADLEAF1)
        parent_oname = new_args['parent']
        del new_args['parent']

        parent_olev = OrganizationLevel.objects.get(name=parent_oname)
        new_args['parent'] = parent_olev
        newolev = None
        with self.assertRaises(ValidationError) as cm:
            newolev = OrganizationLevel.objects.create(**new_args)

        if newolev is not None:
            # Cleanup in case did not raise exception
            newolev.delete()

        if 'orglevel_exceptions' in VERBOSE_TESTS:
            exc = cm.exception
            sys.stderr.write('[DEBUG] {}: got exc={}: {}\n'.format(
                testname, type(exc), exc))
        return


    def test_orglevel_add_delete_root_tier(self):
        """Test that we can successfully add/delete_organization_level for root orglevel"""
        # Find any Organizations at root level before we add new root
        hlist = OrganizationLevel.generate_orglevel_hierarchy_list()
        old_root_olev = hlist[0]
        old_root_orgs = Organization.objects.filter(
                organization_level=old_root_olev).order_by('pk')

        #parent_oname = NEW_ORGLEVEL_ROOT['parent']
        #parent_olev = OrganizationLevel.objects.get(name=parent_oname)
        new_args = dict(NEW_ORGLEVEL_ROOT)
        #del new_args['parent']
        #new_args['parent'] = parent_olev

        try:
            # Add OrgLevel
            newolev = OrganizationLevel.add_organization_level(**new_args)
        except Exception as exc:
            self.fail('exception raised on add_organization_level on new root OrgLevel: {}'.format(
                exc))

        # Make sure OrgLevel hierarchy is correct
        hlist = OrganizationLevel.generate_orglevel_hierarchy_list()
        got = self.orglevels_to_dicts(hlist)
        expected = list(EXPECTED_BASE_ORGLEVEL_HIERARCHY)
        # Replace old root in expected with a copy 
        expected[0] = dict(expected[0])
        # and change parent 
        expected[0]['parent'] = NEW_ORGLEVEL_ROOT['name']
        # And prepend new root
        expected.insert(0, NEW_ORGLEVEL_ROOT)
        self.assertEqual(got, expected)

        # Make sure Organization hierarchy is correct
        got = self.orgs_to_dicts()
        # Generate expected results based on EXPECTED_BASE_ORGS
        newroot_fcode='Unknown1'
        newroot = {
            'fullcode': newroot_fcode,
            'orglevel': NEW_ORGLEVEL_ROOT['name'],
            'code': newroot_fcode,
            'shortname': 'Unknown1',
            'longname': 'Container for Unknown organizations1',
            'is_selectable_for_project': False,
            'is_selectable_for_user': False,
            'parent': None,
        }
        expected = [ newroot ]
        for tmporg in EXPECTED_BASE_ORGS:
            neworg = dict(tmporg)
            neworg['fullcode'] = '{}-{}'.format(
                    newroot_fcode, neworg['fullcode'])
            if neworg['parent'] is None:
                neworg['parent'] = newroot_fcode
            else:
                neworg['parent'] = '{}-{}'.format(
                        newroot_fcode, neworg['parent'])
            expected.append(neworg)
        #end: for tmporg in EXPECTED_BASE_ORGS
        self.assertEqual(got, expected)

        new_root_org = None
        if old_root_orgs:
            # Check that we have a new root level organization
            # (only happens if there was previously at least one root level org)
            qset = Organization.objects.filter(organization_level=newolev)
            self.assertEqual(len(qset), 1, msg='Expected a single root level Organization')
            new_root_org = qset[0]

            # And that children of this new root org are the old root orgs
            # We compare pk's of orgs as Orgs themselves have different parents
            new_subroot_orgs = Organization.objects.filter(
                    parent=new_root_org).order_by('pk')

            got = [ x.pk for x in new_subroot_orgs ]
            expected = [ x.pk for x in old_root_orgs ]
            self.assertEqual(got, expected, msg='Old root orgs now under new root org')

        # Delete the newly created root Organization
        if new_root_org is not None:
            # First we must delete the new root org and set old_root_orgs' parents to None
            #(only if previously had an root level org)
            try:
                Organization.disable_validation_checks(True)
                for org in new_subroot_orgs:
                    org.parent = None
                    org.save()
                new_root_org.delete()
                Organization.disable_validation_checks(False)
            except Exception as exc:
                self.fail('exception raised on deleting new placeholder '
                    'root Org: {}'.format(exc))

        # Delete the newly created root OrganizationLevel
        try:
            newolev.delete_organization_level()
        except Exception as exc:
            self.fail('exception raised on delete_organization_level for new root: {}'.format(
                exc))

        # Make sure OrgLevel hierarchy is correct
        hlist = OrganizationLevel.generate_orglevel_hierarchy_list()
        got = self.orglevels_to_dicts(hlist)
        expected = list(EXPECTED_BASE_ORGLEVEL_HIERARCHY)
        self.assertEqual(got, expected)

        return

    def test_orglevel_add_delete_middle_tier(self):
        """Test that we can successfully add/delete_organization_level for middle orglevel"""
        parent_oname = NEW_ORGLEVEL_MIDDLE['parent']
        parent_olev = OrganizationLevel.objects.get(name=parent_oname)
        new_args = dict(NEW_ORGLEVEL_MIDDLE)
        del new_args['parent']
        new_args['parent'] = parent_olev

        # Cache original org hier list
        orig_hlist = OrganizationLevel.generate_orglevel_hierarchy_list()

        try:
            # Add OrgLevel
            newolev = OrganizationLevel.add_organization_level(**new_args)
        except Exception as exc:
            self.fail('exception raised on add_organization_level on new '
                'middle OrgLevel: {}'.format(exc))

        # Make sure OrgLevel hierarchy is correct
        hlist = OrganizationLevel.generate_orglevel_hierarchy_list()
        got = self.orglevels_to_dicts(hlist)
        # Generate expected OrgLevel List
        expected = []
        below_new = False
        for raworg in EXPECTED_BASE_ORGLEVEL_HIERARCHY:
            org = dict(raworg)
            if below_new:
                if org['parent'] == parent_oname:
                    org['parent'] = NEW_ORGLEVEL_MIDDLE['name']
                expected.append(org)
            else:
                if org['name'] == parent_oname:
                    below_new = True
                expected.append(org)
                new = { 
                        'name': new_args['name'],
                        'level': new_args['level'],
                        'parent': parent_oname,
                        'export_to_xdmod': True,
                    }
                expected.append(new)

        #end: for raworg
        self.assertEqual(got, expected)

        # Make sure Organization hierarchy is correct
        got = self.orgs_to_dicts()
        expected = [ ]
        added_new = False
        tmpcodes = {
                'UMD-CMNS': 'UMD-placeholderCMNS-CMNS',
                'UMD-ENGR': 'UMD-placeholderENGR-ENGR',
                'UMB-SoM': 'UMB-placeholderSoM-SoM',
                'UMB-SoD': 'UMB-placeholderSoD-SoD',
            }
        for raworg in EXPECTED_BASE_ORGS:
            org = dict(raworg)
            fullcode = org['fullcode']
            parent = org['parent']
            if fullcode == 'UMB' or fullcode == 'UMD' or fullcode == 'Unknown':
                expected.append(org)
            else:
                if fullcode in tmpcodes:
                    org['parent'] = org['parent'] + '-placeholder' + org['code']
                    if not added_new:
                        expected.extend(NEW_ORGS_CAMPUS)
                    added_new = True
                for tmpcode, newcode in tmpcodes.items():
                    if fullcode.startswith(tmpcode):
                        org['fullcode'] = fullcode.replace(tmpcode, newcode, 1)
                        #org['shortname'] = 'placeholder' + org['shortname'] 
                        #org['longname'] = 'placeholder' + org['longname'] 
                    if parent.startswith(tmpcode):
                        org['parent'] = parent.replace(tmpcode, newcode, 1)
                expected.append(org)
                #end: for tmpcode, newcode in tmpcodes.items()
            #end: if fullcode in tmpcodes
        #end: for raworg in EXPECTED_BASE_ORGS
        self.assertEqual(got, expected)

        return

    def test_orglevel_validate_fails_on_bad_root(self):
        """Test that validate_orglevel_hierarchy fails on invalid hierarchy (bad root)"""
        testname = 'orglevel_validate_fails_on_bad_root'
        # Force the addition of an invalid root tier
        new_args = dict(NEW_ORGLEVEL_ROOT)
        newolev = None
        OrganizationLevel.disable_validation_checks(True)
        newolev = OrganizationLevel.objects.create(**new_args)
        OrganizationLevel.disable_validation_checks(False)

        with self.assertRaises(ValidationError) as cm:
            OrganizationLevel.validate_orglevel_hierarchy()

        # Cleanup
        if newolev:
            OrganizationLevel.disable_validation_checks(True)
            newolev.delete()
            OrganizationLevel.disable_validation_checks(False)

        if 'orglevel_exceptions' in VERBOSE_TESTS:
            exc = cm.exception
            sys.stderr.write('[DEBUG] {}: got exc={}: {}\n'.format(
                testname, type(exc), exc))
        return

    def test_orglevel_validate_warns_if_checks_disabled(self):
        """Test that validate_orglevel_hierarchy warns on disable_validation_checks"""
        testname = 'orglevel_validate_warns_if_checks_disabled'
        OrganizationLevel.disable_validation_checks(True)
        with self.assertWarns(Warning) as cm:
            OrganizationLevel.validate_orglevel_hierarchy()

        # Cleanup
        OrganizationLevel.disable_validation_checks(False)

        if 'orglevel_exceptions' in VERBOSE_TESTS:
            exc = cm.warning
            sys.stderr.write('[DEBUG] {}: got warning={}: {}\n'.format(
                testname, type(exc), exc))
        return

    def test_orglevel_validate_fails_on_bad_leaf(self):
        """Test that validate_orglevel_hierarchy fails on invalid hierarchy (bad leaf)"""
        testname = 'orglevel_validate_fails_on_bad_leaf'
        # Force the addition of an invalid badleaf tier
        new_args = dict(NEW_ORGLEVEL_BADLEAF1)
        parent_oname = new_args['parent']
        del new_args['parent']

        parent_olev = OrganizationLevel.objects.get(name=parent_oname)
        new_args['parent'] = parent_olev
        newolev = None

        OrganizationLevel.disable_validation_checks(True)
        newolev = OrganizationLevel.objects.create(**new_args)
        OrganizationLevel.disable_validation_checks(False)

        with self.assertRaises(ValidationError) as cm:
            OrganizationLevel.validate_orglevel_hierarchy()

        # Cleanup
        if newolev:
            OrganizationLevel.disable_validation_checks(True)
            newolev.delete()
            OrganizationLevel.disable_validation_checks(False)

        if 'orglevel_exceptions' in VERBOSE_TESTS:
            exc = cm.exception
            sys.stderr.write('[DEBUG] {}: got exc={}: {}\n'.format(
                testname, type(exc), exc))
        return

    def test_org_dont_naive_add_skipped_parent(self):
        """Test that we cannot naively add an org which skips an orglevel"""
        testname = 'org_dont_naive_add_skipped_parent'
        # Try adding an org whose parent skips an org level
        new_args = {}
        olevname = NEW_BAD_ORG1['orglevel']
        olev = OrganizationLevel.objects.get(name=olevname)
        new_args['organization_level'] = olev
        for tmp in ('code', 'shortname', 'longname', 
                'is_selectable_for_user', 'is_selectable_for_project' ):
            new_args[tmp] = NEW_BAD_ORG1[tmp]
        new = None
        with self.assertRaises(ValidationError) as cm:
            new = Organization.objects.create(**new_args)

        if new is not None:
            # Cleanup in case did not raise exception
            new.delete()

        if 'org_exceptions' in VERBOSE_TESTS:
            exc = cm.exception
            sys.stderr.write('[DEBUG] {}: got exc={}: {}\n'.format(
                testname, type(exc), exc))
        return

    def test_org_validation_fails_on_skipped_orglevel(self):
        """Test that we cannot naively add an org which skips an orglevel"""
        testname = 'org_validation_fails_on_skipped_orglevel'
        # Try adding an org whose parent skips an org level
        new_args = {}
        olevname = NEW_BAD_ORG1['orglevel']
        olev = OrganizationLevel.objects.get(name=olevname)
        new_args['organization_level'] = olev
        for tmp in ('code', 'shortname', 'longname', 
                'is_selectable_for_user', 'is_selectable_for_project' ):
            new_args[tmp] = NEW_BAD_ORG1[tmp]
        new = None
        Organization.disable_validation_checks(True)
        new = Organization.objects.create(**new_args)
        Organization.disable_validation_checks(False)


        with self.assertRaises(ValidationError) as cm:
            Organization.validate_organization_hierarchy()

        if new is not None:
            # Cleanup in case did not raise exception
            new.delete()

        if 'org_exceptions' in VERBOSE_TESTS:
            exc = cm.exception
            sys.stderr.write('[DEBUG] {}: got exc={}: {}\n'.format(
                testname, type(exc), exc))
        return

