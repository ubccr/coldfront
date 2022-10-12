import sys
import os

from coldfront.core.utils.libtest import (
        TestFixtureBuilderCommand,
        verbose_msg,
        create_aattributes_from_dictlist,
        create_allocationattributetypes_from_dictlist,
        create_allocations_from_dictlist,
        create_organizations_from_dictlist,
        create_organization_levels_from_dictlist,
        create_projects_from_dictlist,
        create_rattributes_from_dictlist,
        create_resourcetypes_from_dictlist,
        create_resourceattributetypes_from_dictlist,
        create_resources_from_dictlist,
        create_users_from_dictlist,
    )


from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

                                        
DEFAULT_FIXTURE_NAME='organization_test_data.json'
DEFAULT_FIXTURE_DIR='./coldfront/coldfront/core/utils/fixtures'



class Command(TestFixtureBuilderCommand):
    default_fixture_name = 'organization_test_data.json'

    def create_data(self, options):
        """Override base class method to actually generate data."""
        self.create_org_levels(options)
        self.create_orgs(options)
        self.create_users(options)
        self.create_resources(options)
        self.create_projects(options)
        self.create_allocation_attribute_types(options)
        self.create_allocations(options)
        return

    def create_org_levels(self, options):
        """Create OrgLevels for test data"""
        orglevels = [
            { 
                'name':'University', 
                'level': 40, 
                'parent': None,
            },
            { 
                'name': 'College', 
                'level': 30, 
                'parent': 'University',
            },
            { 
                'name': 'Department', 
                'level': 20, 
                'parent': 'College',
            },
        ]
        create_organization_levels_from_dictlist(
                dlist=orglevels, verbosity=options)
        return

    def create_orgs(self, options):
        """Create Orgs for test data"""
        orgs = [
                # University level
                {   'code': 'Unknown',
                    'organization_level': 'University',
                    'parent': None,
                    'shortname': 'Unknown',
                    'longname': 'Container for Unknown organizations',
                    'is_selectable_for_user': False,
                    'is_selectable_for_project': False,
                },
                {   'code': 'UMD',
                    'organization_level': 'University',
                    'parent': None,
                    'shortname': 'UMCP',
                    'longname': 'University of Maryland',
                    'is_selectable_for_user': False,
                    'is_selectable_for_project': False,
                },
                {   'code': 'UMB',
                    'organization_level': 'University',
                    'parent': None,
                    'shortname': 'UMD Baltimore',
                    'longname': 'University of Maryland, Baltimore',
                    'is_selectable_for_user': False,
                    'is_selectable_for_project': False,
                },
                # College level - UMD
                {   'code': 'CMNS',
                    'organization_level': 'College',
                    'parent': 'UMD',
                    'shortname': 'CMNS',
                    'longname': 'College of Computer, Mathematical, and Natural Sciences',
                    'is_selectable_for_user': False,
                    'is_selectable_for_project': False,
                },
                {   'code': 'ENGR',
                    'organization_level': 'College',
                    'parent': 'UMD',
                    'shortname': 'Engineering',
                    'longname': 'School of Engineering',
                    'is_selectable_for_user': False,
                    'is_selectable_for_project': False,
                },
                # Departmental level - UMD-CMNS
                {   'code': 'ASTR',
                    'organization_level': 'Department',
                    'parent': 'UMD-CMNS',
                    'shortname': 'Astronomy',
                    'longname': 'Astronomy Department',
                    'is_selectable_for_user': True,
                    'is_selectable_for_project': True,
                    'directory2organization': [
                            'CMNS-Astronomy',
                        ],
                },
                {   'code': 'PHYS',
                    'organization_level': 'Department',
                    'parent': 'UMD-CMNS',
                    'shortname': 'Physics',
                    'longname': 'Physics Department',
                    'is_selectable_for_user': True,
                    'is_selectable_for_project': True,
                    'directory2organization': [
                            'CMNS-Physics',
                            'CMNS-Physics-Joint Quantum Institute',
                            'CMNS-Physics-Quantum Materials Center',
                        ],
                },
                # Departmental level - UMD-ENGR
                {   'code': 'ENAE',
                    'organization_level': 'Department',
                    'parent': 'UMD-ENGR',
                    'shortname': 'Aeronautical Eng',
                    'longname': 'Dept of Aeronautical Engineering',
                    'is_selectable_for_user': True,
                    'is_selectable_for_project': True,
                    'directory2organization': [
                            'ENGR-Aerospace Engineering',
                        ]
                },
                {   'code': 'ENMA',
                    'organization_level': 'Department',
                    'parent': 'UMD-ENGR',
                    'shortname': 'Materials Eng',
                    'longname': 'Dept of Materials Engineering',
                    'is_selectable_for_user': True,
                    'is_selectable_for_project': True,
                    'directory2organization': [
                            'ENGR-Materials Science & Engineering',
                        ]
                },
                # College level - UMB
                {   'code': 'SoM',
                    'organization_level': 'College',
                    'parent': 'UMB',
                    'shortname': 'Medicine',
                    'longname': 'School of Medicine',
                    'is_selectable_for_user': False,
                    'is_selectable_for_project': False,
                },
                {   'code': 'SoD',
                    'organization_level': 'College',
                    'parent': 'UMB',
                    'shortname': 'Dentistry',
                    'longname': 'School of Dentistry',
                    'is_selectable_for_user': False,
                    'is_selectable_for_project': False,
                },
                # Departmental level - UMB-SoM
                {   'code': 'Psych',
                    'organization_level': 'Department',
                    'parent': 'UMB-SoM',
                    'shortname': 'Psychiatry',
                    'longname': 'Psychiatry Department',
                    'is_selectable_for_user': True,
                    'is_selectable_for_project': True,
                    'directory2organization': [
                            'Medicine-Psychiatry',
                        ]
                },
                {   'code': 'Surg',
                    'organization_level': 'Department',
                    'parent': 'UMB-SoM',
                    'shortname': 'Surgery',
                    'longname': 'Surgery Department',
                    'is_selectable_for_user': True,
                    'is_selectable_for_project': True,
                    'directory2organization': [
                            'Medicine-Surgery',
                        ]
                },
                # Departmental level - UMB-SoD
                {   'code': 'NeuPain',
                    'organization_level': 'Department',
                    'parent': 'UMB-SoD',
                    'shortname': 'Neural and Pain',
                    'longname': 'Department of Neural and Pain Sciences',
                    'is_selectable_for_user': True,
                    'is_selectable_for_project': True,
                    'directory2organization': [
                            'Dentistry-Neural and Pain Sciences',
                        ]
                },
                {   'code': 'Perio',
                    'organization_level': 'Department',
                    'parent': 'UMB-SoD',
                    'shortname': 'Periodontics',
                    'longname': 'Division of Periodontics',
                    'is_selectable_for_user': True,
                    'is_selectable_for_project': True,
                    'directory2organization': [
                            'Dentistry-Periodontics'
                        ]
                },
            ]
        create_organizations_from_dictlist(
                dlist=orgs, verbosity=options)
        return
                    
    def create_users(self, options):
        """Create Users for test data"""
        users = [
                # Users
                {   'username': 'newton',
                    'first_name': 'Isaac',
                    'last_name': 'Newton',
                    'organizations': [
                            'UMD-CMNS-PHYS',
                        ],
                    'is_pi': False,
                },
                {   'username': 'einstein',
                    'first_name': 'Albert',
                    'last_name': 'Einstein',
                    'organizations': [
                            'UMD-CMNS-PHYS',
                        ],
                    'is_pi': True,
                },
                {   'username': 'freud',
                    'first_name': 'Sigmund',
                    'last_name': 'Freud',
                    'organizations': [
                            'UMB-SoM-Psych',
                        ],
                    'is_pi': True,
                },
                {   'username': 'hawkeye',
                    'first_name': 'Benjamin',
                    'last_name': 'Pierce',
                    'organizations': [
                            'UMB-SoM-Surg',
                        ],
                    'is_pi': True,
                },
                {   'username': 'orville',
                    'first_name': 'Orville',
                    'last_name': 'Wright',
                    'organizations': [
                            'UMD-ENGR-ENAE',
                        ],
                    'is_pi': True,
                },
                {   'username': 'wilbur',
                    'first_name': 'Wilbur',
                    'last_name': 'Wright',
                    'organizations': [
                            'UMD-ENGR-ENAE',
                            'UMD-CMNS-PHYS',
                        ],
                    'is_pi': False,
                },
            ]
        create_users_from_dictlist(
                dlist=users, verbosity=options)
        return
                    
    def create_resources(self, options):
        """Create Resources for test data"""
        resources = [
                { 
                    'name': 'University HPC',
                    'description': 'Main University HPC',
                    'is_available': True,
                    'is_public': True,
                    'is_allocatable': True,
                    'requires_payment': False,
                    'parent_resource': None,
                    'resource_type': 'Cluster',
                    'resource_attributes': [
                        {   'resource_attribute_type': 'slurm_cluster',
                            'value': 'mainhpc',
                        },
                    ],
                },
            ]
        create_resources_from_dictlist(
                dlist=resources, verbosity=options)
        return

    def create_projects(self, options):
        """Create Projects for test data"""
        projects = [
                { 
                    'title': 'Gravitational Studies',
                    'description': 'Study of Gravity',
                    'pi': 'einstein',
                    'field_of_science': 'Gravitational Physics',
                    'force_review': False,
                    'requires_review': True,
                    'organizations': [
                            'UMD-CMNS-PHYS',
                        ],
                    'users':
                        [   'newton',
                        ],
                    'managers':
                        [   'einstein',
                        ]
                },
                { 
                    'title': 'Hyposonic Flight',
                    'description': 'Study of Flight at very low speeds',
                    'pi': 'orville',
                    'field_of_science': 'Other',
                    'force_review': False,
                    'requires_review': True,
                    'organizations': [
                            'UMD-ENGR-ENAE',
                            'UMD-CMNS-PHYS',
                        ],
                    'users':
                        [   'wilbur',
                        ],
                    'managers':
                        [   'orville',
                        ]
                },
                { 
                    'title': 'Artificial Id',
                    'description': 'Attempts to build artificial intelligence with ego and id',
                    'pi': 'freud',
                    'field_of_science': 'Information, Robotics, and Intelligent Systems',
                    'force_review': False,
                    'requires_review': True,
                    'organizations': [
                            'UMB-SoM-Psych',
                        ],
                },
                { 
                    'title': 'Meatball Surgery',
                    'description': 'Surgery under battlefield conditions',
                    'pi': 'hawkeye',
                    'field_of_science': 'Physiology and Behavior',
                    'force_review': False,
                    'requires_review': True,
                    'organizations': [
                            'UMB-SoM-Surg',
                        ],
                },

            ]
        create_projects_from_dictlist(
                dlist=projects, verbosity=options)
        return

    def create_allocation_attribute_types(self, options):
        """Create AllocationAttributeTypes for test data"""
        aatypes = [
                { 
                    'name': 'slurm_account_name',
                    'attribute_type_name': 'Text',
                    'has_usage': False,
                    'is_required': False,
                    'is_unique': False,
                    'is_private': False,
                },
                { 
                    'name': 'slurm_specs',
                },
                { 
                    'name': 'slurm_user_specs',
                },
                { 
                    'name': 'xdmod_allocation_code',
                },
                { 
                    'name': 'xdmod_allocation_name',
                },
                { 
                    'name': 'xdmod_project_code',
                },
            ]
        create_allocationattributetypes_from_dictlist(
                dlist=aatypes, verbosity=options)
        return

    def create_allocations(self, options):
        """Create Allocations for test data"""
        allocations = [
                { 
                    'description': 'einstein-alloc',
                    'project': 'Gravitational Studies',
                    'resources': ['University HPC' ],
                    'justification': 'Must warp space-time',
                    'allocation_attributes': [
                        {   'allocation_attribute_type': 'slurm_account_name',
                            'value': 'einstein-alloc',
                        },
                    ],

                },
                { 
                    'description': 'wright-alloc',
                    'project': 'Hyposonic Flight',
                    'resources': ['University HPC' ],
                    'justification': 'I need CPU',
                    'allocation_attributes': [
                        {   'allocation_attribute_type': 'slurm_account_name',
                            'value': 'wright-alloc',
                        },
                        {   'allocation_attribute_type': 'xdmod_project_code',
                            'value': 'wright-proj',
                        },
                        {   'allocation_attribute_type': 'xdmod_allocation_code',
                            'value': 'hyposonicflight',
                        },
                    ],

                },
                { 
                    'description': 'wilbur-alloc',
                    'project': 'Hyposonic Flight',
                    'resources': ['University HPC' ],
                    'justification': 'Wilbur needs more CPU',
                    'users': [ 'wilbur' ],
                    'allocation_attributes': [
                        {   'allocation_attribute_type': 'slurm_account_name',
                            'value': 'wilbur-alloc',
                        },
                        {   'allocation_attribute_type': 'xdmod_project_code',
                            'value': 'wilbur-proj',
                        },
                        {   'allocation_attribute_type': 'xdmod_allocation_code',
                            'value': 'hyposonicflight',
                        },
                    ],

                },
                { 
                    'description': 'orville-alloc',
                    'project': 'Hyposonic Flight',
                    'resources': ['University HPC' ],
                    'justification': 'Orville needs more CPU',
                    'users': [ 'orville' ],
                    'allocation_attributes': [
                        {   'allocation_attribute_type': 'slurm_account_name',
                            'value': 'orville-alloc',
                        },
                        {   'allocation_attribute_type': 'xdmod_project_code',
                            'value': 'orville-proj',
                        },
                        {   'allocation_attribute_type': 'xdmod_allocation_name',
                            'value': 'Orville Wright allocation',
                        },
                    ],

                },
                { 
                    'description': 'freud-alloc',
                    'project': 'Artificial Id',
                    'resources': ['University HPC' ],
                    'allocation_attributes': [
                        {   'allocation_attribute_type': 'slurm_account_name',
                            'value': 'freud-alloc',
                        },
                    ],

                },
                { 
                    'description': 'hawkeye-alloc',
                    'project': 'Meatball Surgery',
                    'resources': ['University HPC' ],
                    'allocation_attributes': [
                        {   'allocation_attribute_type': 'slurm_account_name',
                            'value': 'hawkeye-alloc',
                        },
                    ],

                },
            ]
        create_allocations_from_dictlist(
                dlist=allocations, verbosity=options)
        return
