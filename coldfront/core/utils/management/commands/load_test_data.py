# SPDX-FileCopyrightText: (C) ColdFront Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

import datetime

from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from coldfront.core.allocation.models import (
    Allocation,
    AllocationAttribute,
    AllocationAttributeType,
    AllocationStatusChoice,
    AllocationUser,
    AllocationUserStatusChoice,
)
from coldfront.core.field_of_science.models import FieldOfScience
from coldfront.core.grant.models import Grant, GrantFundingAgency, GrantStatusChoice
from coldfront.core.project.models import (
    AttributeType,
    Project,
    ProjectAttribute,
    ProjectAttributeType,
    ProjectStatusChoice,
    ProjectUser,
    ProjectUserRoleChoice,
    ProjectUserStatusChoice,
)
from coldfront.core.publication.models import Publication, PublicationSource
from coldfront.core.resource.models import Resource, ResourceAttribute, ResourceAttributeType, ResourceType

base_dir = settings.BASE_DIR

# first, last
Users = [
    "Carl	Gray",  # PI#1
    "Stephanie	Foster",  # PI#2
    "Charles	Simmons",  # Director
    "Andrea	Stewart",
    "Alice	Rivera",
    "Frank	Hernandez",
    "Justin	James",
    "Randy	Perry",
    "Carol	Lee",
    "Susan	Hughes",
    "Jose	Martin",
    "Joe	Roberts",
    "Howard	Nelson",
    "Patricia	Moore",
    "Jessica	Alexander",
    "Jesse	Russell",
    "Shirley	Price",
    "Julie	Phillips",
    "Kathy	Jenkins",
    "James	Hill",
    "Tammy	Howard",
    "Lisa	Coleman",
    "Denise	Adams",
    "Shawn	Williams",
    "Ernest	Reed",
    "Larry	Ramirez",
    "Kathleen	Garcia",
    "Jennifer	Jones",
    "Irene	Anderson",
    "Beverly	Mitchell",
    "Peter	Patterson",
    "Eugene	Griffin",
    "Jimmy	Lewis",
    "Margaret	Turner",
    "Julia	Peterson",
    "Amanda	Johnson",
    "Christina	Morris",
    "Cynthia	Carter",
    "Wayne	Murphy",
    "Ronald	Sanders",
    "Lillian	Bell",
    "Harold	Lopez",
    "Roger	Wilson",
    "Jane	Edwards",
    "Billy	Perez",
    "Jane	Butler",
    "John	Smith",
    "John	Long",
    "Jane	Martinez",
    "John	Cooper",
]


dois = [
    "10.1016/j.nuclphysb.2014.08.011",
    "10.1103/PhysRevB.81.014411",
    "10.1103/PhysRevB.82.014421",
    "10.1103/PhysRevB.83.014401",
    "10.1103/PhysRevB.84.014503",
    "10.1103/PhysRevB.85.014111",
    "10.1103/PhysRevB.92.014205",
    "10.1103/PhysRevB.91.140409",
]


# resource_type, parent_resource, name, description, is_available, is_public, is_allocatable
resources = [
    # Clusters
    ("Cluster", None, "University HPC", "University Academic Cluster", True, True, True),
    ("Cluster", None, "Chemistry", "Chemistry Cluster", True, False, False),
    ("Cluster", None, "Physics", "Physics Cluster", True, False, False),
    ("Cluster", None, "Industry", "Industry Cluster", True, False, False),
    ("Cluster", None, "University Metered HPC", "SU metered Cluster", True, True, True),
    # Cluster Partitions scavengers
    (
        "Cluster Partition",
        "Chemistry",
        "Chemistry-scavenger",
        "Scavenger partition on Chemistry cluster",
        True,
        False,
        False,
    ),
    ("Cluster Partition", "Physics", "Physics-scavenger", "Scavenger partition on Physics cluster", True, False, False),
    (
        "Cluster Partition",
        "Industry",
        "Industry-scavenger",
        "Scavenger partition on Industry cluster",
        True,
        False,
        False,
    ),
    # Cluster Partitions Users
    ("Cluster Partition", "Chemistry", "Chemistry-cgray", "Carl Gray's nodes", True, False, True),
    ("Cluster Partition", "Physics", "Physics-sfoster", "Stephanie Foster's nodes", True, False, True),
    # Servers
    ("Server", None, "server-cgray", "Server for Carl Gray's research lab", True, False, True),
    ("Server", None, "server-sfoster", "Server for Stephanie Foster's research lab", True, False, True),
    # Storage
    ("Storage", None, "Budgetstorage", "Low-tier storage option - NOT BACKED UP", True, True, True),
    ("Storage", None, "ProjectStorage", "Enterprise-level storage - BACKED UP DAILY", True, True, True),
    # Cloud
    ("Cloud", None, "University Cloud", "University Research Cloud", True, True, True),
    (
        "Storage",
        "University Cloud",
        "University Cloud Storage",
        "Storage available to cloud instances",
        True,
        True,
        True,
    ),
]


class Command(BaseCommand):
    def handle(self, *args, **options):
        for user in Users:
            first_name, last_name = user.split()
            username = first_name[0].lower() + last_name.lower().strip()
            email = username + "@example.com"
            User.objects.get_or_create(
                first_name=first_name.strip(),
                last_name=last_name.strip(),
                username=username.strip(),
                email=email.strip(),
            )

        admin_user, _ = User.objects.get_or_create(username="admin")
        admin_user.is_superuser = True
        admin_user.is_staff = True
        admin_user.save()

        for user in User.objects.all():
            user.set_password("test1234")
            user.save()

        for resource in resources:
            resource_type, parent_resource, name, description, is_available, is_public, is_allocatable = resource
            resource_type_obj = ResourceType.objects.get(name=resource_type)
            if parent_resource is not None:
                parent_resource_obj = Resource.objects.get(name=parent_resource)
            else:
                parent_resource_obj = None

            Resource.objects.get_or_create(
                resource_type=resource_type_obj,
                parent_resource=parent_resource_obj,
                name=name,
                description=description,
                is_available=is_available,
                is_public=is_public,
                is_allocatable=is_allocatable,
            )

        resource_obj = Resource.objects.get(name="server-cgray")
        resource_obj.allowed_users.add(User.objects.get(username="cgray"))
        resource_obj = Resource.objects.get(name="server-sfoster")
        resource_obj.allowed_users.add(User.objects.get(username="sfoster"))

        pi1 = User.objects.get(username="cgray")
        pi1.userprofile.is_pi = True
        pi1.save()
        project_obj, _ = Project.objects.get_or_create(
            pi=pi1,
            title="Angular momentum in QGP holography",
            description="We want to estimate the quark chemical potential of a rotating sample of plasma.",
            field_of_science=FieldOfScience.objects.get(description="Chemistry"),
            status=ProjectStatusChoice.objects.get(name="Active"),
            force_review=True,
        )

        AttributeType.objects.get_or_create(name="Int")

        ProjectAttributeType.objects.get_or_create(
            attribute_type=AttributeType.objects.get(name="Text"),
            name="Project ID",
            is_private=False,
        )

        ProjectAttributeType.objects.get_or_create(
            attribute_type=AttributeType.objects.get(name="Int"),
            name="Account Number",
            is_private=True,
        )

        ProjectAttribute.objects.get_or_create(
            proj_attr_type=ProjectAttributeType.objects.get(name="Project ID"),
            project=project_obj,
            value=1242021,
        )

        ProjectAttribute.objects.get_or_create(
            proj_attr_type=ProjectAttributeType.objects.get(name="Account Number"),
            project=project_obj,
            value=1756522,
        )

        univ_hpc = Resource.objects.get(name="University HPC")
        for scavanger in (
            "Chemistry-scavenger",
            "Physics-scavenger",
            "Industry-scavenger",
        ):
            resource_obj = Resource.objects.get(name=scavanger)
            univ_hpc.linked_resources.add(resource_obj)
            univ_hpc.save()

        publication_source = PublicationSource.objects.get(name="doi")
        # for title, author, year, unique_id, source in (
        #     ('Angular momentum in QGP holography', 'Brett McInnes',
        #      2014, '10.1016/j.nuclphysb.2014.08.011', 'doi'),
        #     ('Robust ferroelectric state in multiferroicMn1-xZnxWO4',
        #      'R. P. Chaudhury and F. Ye and J. A. Fernandez-Baca and B. Lorenz and Y. Q. Wang and Y. Y. Sun and H. A. Mook and C. W. Chu',
        #      2011,
        #      '10.1103/PhysRevB.83.014401',
        #      'doi'
        #      ),
        #     ('Extreme sensitivity of a frustrated quantum magnet:Cs2CuCl4',
        #      'Oleg A. Starykh and Hosho Katsura and Leon Balents',
        #      2010,
        #      '10.1103/PhysRevB.82.014421',
        #      'doi'
        #      ),
        #     ('Magnetic excitations in the spinel compoundLix[Mn1.96Li0.04]O4(x=0.2,0.6,0.8,1.0): How a classical system can mimic quantum critical scaling',
        #      'Thomas Heitmann and Alexander Schmets and John Gaddy and Jagat Lamsal and Marcus Petrovic and Thomas Vojta and Wouter Montfrooij',
        #      2010,
        #      '10.1103/PhysRevB.81.014411',
        #      'doi'
        #      ),
        # ):
        #     Publication.objects.get_or_create(
        #         project=project_obj,
        #         title=title,
        #         author=author,
        #         year=year,
        #         unique_id=unique_id,
        #         source=publication_source
        #     )

        # start_date = datetime.datetime.now()
        # end_date = datetime.datetime.now() + relativedelta(days=900)

        # Grant.objects.get_or_create(
        #     project=project_obj,
        #     title='Angular momentum in QGP holography',
        #     grant_number='12345',
        #     role='CoPI',
        #     grant_pi_full_name='John Doe',
        #     funding_agency=GrantFundingAgency.objects.get(
        #         name='National Science Foundation (NSF)'),
        #     grant_start=start_date,
        #     grant_end=end_date,
        #     percent_credit=20.0,
        #     direct_funding=600000.0,
        #     total_amount_awarded=3000000.0,
        #     status=GrantStatusChoice.objects.get(name='Active')
        # )

        project_user_obj, _ = ProjectUser.objects.get_or_create(
            user=pi1,
            project=project_obj,
            role=ProjectUserRoleChoice.objects.get(name="Manager"),
            status=ProjectUserStatusChoice.objects.get(name="Active"),
        )

        start_date = datetime.datetime.now()
        end_date = datetime.datetime.now() + relativedelta(days=365)

        # Add PI cluster
        allocation_obj, _ = Allocation.objects.get_or_create(
            project=project_obj,
            status=AllocationStatusChoice.objects.get(name="Active"),
            start_date=start_date,
            end_date=end_date,
            is_changeable=True,
            justification="I need access to my nodes.",
        )

        allocation_obj.resources.add(Resource.objects.get(name="Chemistry-cgray"))
        allocation_obj.save()

        allocation_attribute_type_obj = AllocationAttributeType.objects.get(name="slurm_account_name")
        AllocationAttribute.objects.get_or_create(
            allocation_attribute_type=allocation_attribute_type_obj, allocation=allocation_obj, value="cgray"
        )

        allocation_attribute_type_obj = AllocationAttributeType.objects.get(name="slurm_user_specs")
        AllocationAttribute.objects.get_or_create(
            allocation_attribute_type=allocation_attribute_type_obj, allocation=allocation_obj, value="Fairshare=parent"
        )

        AllocationUser.objects.create(
            allocation=allocation_obj, user=pi1, status=AllocationUserStatusChoice.objects.get(name="Active")
        )
        # Add university cluster
        allocation_obj, _ = Allocation.objects.get_or_create(
            project=project_obj,
            status=AllocationStatusChoice.objects.get(name="Active"),
            start_date=start_date,
            end_date=datetime.datetime.now() + relativedelta(days=10),
            is_changeable=True,
            justification="I need access to university cluster.",
        )

        allocation_obj.resources.add(Resource.objects.get(name="University HPC"))
        allocation_obj.save()

        allocation_attribute_type_obj = AllocationAttributeType.objects.get(name="slurm_specs")
        AllocationAttribute.objects.get_or_create(
            allocation_attribute_type=allocation_attribute_type_obj,
            allocation=allocation_obj,
            value="Fairshare=100:QOS+=supporters",
        )

        allocation_attribute_type_obj = AllocationAttributeType.objects.get(name="slurm_user_specs")
        AllocationAttribute.objects.get_or_create(
            allocation_attribute_type=allocation_attribute_type_obj, allocation=allocation_obj, value="Fairshare=parent"
        )

        allocation_attribute_type_obj = AllocationAttributeType.objects.get(name="slurm_account_name")
        AllocationAttribute.objects.get_or_create(
            allocation_attribute_type=allocation_attribute_type_obj, allocation=allocation_obj, value="cgray"
        )

        allocation_attribute_type_obj = AllocationAttributeType.objects.get(name="SupportersQOS")
        AllocationAttribute.objects.get_or_create(
            allocation_attribute_type=allocation_attribute_type_obj, allocation=allocation_obj, value="Yes"
        )

        allocation_attribute_type_obj = AllocationAttributeType.objects.get(name="SupportersQOSExpireDate")
        AllocationAttribute.objects.get_or_create(
            allocation_attribute_type=allocation_attribute_type_obj, allocation=allocation_obj, value="2022-01-01"
        )

        AllocationUser.objects.create(
            allocation=allocation_obj, user=pi1, status=AllocationUserStatusChoice.objects.get(name="Active")
        )
        # Add project storage
        allocation_obj, _ = Allocation.objects.get_or_create(
            project=project_obj,
            status=AllocationStatusChoice.objects.get(name="Active"),
            start_date=start_date,
            end_date=end_date,
            quantity=10,
            is_changeable=True,
            justification="I need extra storage.",
        )

        allocation_obj.resources.add(Resource.objects.get(name="Budgetstorage"))
        allocation_obj.save()

        AllocationUser.objects.create(
            allocation=allocation_obj, user=pi1, status=AllocationUserStatusChoice.objects.get(name="Active")
        )

        # Add metered allocation
        allocation_obj, _ = Allocation.objects.get_or_create(
            project=project_obj,
            status=AllocationStatusChoice.objects.get(name="Active"),
            start_date=start_date,
            end_date=end_date,
            is_changeable=True,
            justification="I need compute time on metered cluster.",
        )
        allocation_obj.resources.add(Resource.objects.get(name="University Metered HPC"))
        allocation_obj.save()
        allocation_attribute_type_obj = AllocationAttributeType.objects.get(name="slurm_account_name")
        AllocationAttribute.objects.get_or_create(
            allocation_attribute_type=allocation_attribute_type_obj, allocation=allocation_obj, value="cgray-metered"
        )
        allocation_attribute_type_obj = AllocationAttributeType.objects.get(name="Core Usage (Hours)")
        AllocationAttribute.objects.get_or_create(
            allocation_attribute_type=allocation_attribute_type_obj, allocation=allocation_obj, value="150000"
        )
        AllocationUser.objects.create(
            allocation=allocation_obj, user=pi1, status=AllocationUserStatusChoice.objects.get(name="Active")
        )

        pi2 = User.objects.get(username="sfoster")
        pi2.userprofile.is_pi = True
        pi2.save()
        project_obj, _ = Project.objects.get_or_create(
            pi=pi2,
            title="Measuring critical behavior of quantum Hall transitions",
            description="This purpose of this project is to measure the critical behavior of quantum Hall transitions.",
            field_of_science=FieldOfScience.objects.get(description="Physics"),
            status=ProjectStatusChoice.objects.get(name="Active"),
        )

        project_user_obj, _ = ProjectUser.objects.get_or_create(
            user=pi2,
            project=project_obj,
            role=ProjectUserRoleChoice.objects.get(name="Manager"),
            status=ProjectUserStatusChoice.objects.get(name="Active"),
        )

        for title, author, year, journal, unique_id, source in (
            (
                "Lattice constants from semilocal density functionals with zero-point phonon correction",
                "Pan Hao and Yuan Fang and Jianwei Sun and G'abor I. Csonka and Pier H. T. Philipsen and John P. Perdew",
                2012,
                "Physical Review B",
                "10.1103/PhysRevB.85.014111",
                "doi",
            ),
            (
                "Anisotropic magnetocapacitance in ferromagnetic-plate capacitors",
                "J. A. Haigh and C. Ciccarelli and A. C. Betz and A. Irvine and V. Nov'ak and T. Jungwirth and J. Wunderlich",
                2015,
                "Physical Review B",
                "10.1103/PhysRevB.91.140409",
                "doi",
            ),
            (
                "Interaction effects in topological superconducting wires supporting Majorana fermions",
                "E. M. Stoudenmire and Jason Alicea and Oleg A. Starykh and Matthew P.A. Fisher",
                2011,
                "Physical Review B",
                "10.1103/PhysRevB.84.014503",
                "doi",
            ),
            (
                "Logarithmic correlations in quantum Hall plateau transitions",
                "Romain Vasseur",
                2015,
                "Physical Review B",
                "10.1103/PhysRevB.92.014205",
                "doi",
            ),
        ):
            Publication.objects.get_or_create(
                project=project_obj,
                title=title,
                author=author,
                year=year,
                journal=journal,
                unique_id=unique_id,
                source=publication_source,
            )

        start_date = datetime.datetime.now()
        end_date = datetime.datetime.now() + relativedelta(days=900)

        Grant.objects.get_or_create(
            project=project_obj,
            title="Quantum Halls",
            grant_number="12345",
            role="PI",
            grant_pi_full_name="Stephanie Foster",
            funding_agency=GrantFundingAgency.objects.get(name="Department of Defense (DoD)"),
            grant_start=start_date,
            grant_end=end_date,
            percent_credit=20.0,
            direct_funding=200000.0,
            total_amount_awarded=1000000.0,
            status=GrantStatusChoice.objects.get(name="Active"),
        )

        # Add university cloud
        allocation_obj, _ = Allocation.objects.get_or_create(
            project=project_obj,
            status=AllocationStatusChoice.objects.get(name="Active"),
            start_date=start_date,
            end_date=end_date,
            is_changeable=True,
            justification="Need to host my own site.",
        )

        allocation_obj.resources.add(Resource.objects.get(name="University Cloud"))
        allocation_obj.save()

        allocation_attribute_type_obj = AllocationAttributeType.objects.get(name="Cloud Account Name")
        AllocationAttribute.objects.get_or_create(
            allocation_attribute_type=allocation_attribute_type_obj,
            allocation=allocation_obj,
            value="sfoster-openstack",
        )

        allocation_attribute_type_obj = AllocationAttributeType.objects.get(name="Core Usage (Hours)")
        allocation_attribute_obj, _ = AllocationAttribute.objects.get_or_create(
            allocation_attribute_type=allocation_attribute_type_obj, allocation=allocation_obj, value=1000
        )

        allocation_attribute_obj.allocationattributeusage.value = 200
        allocation_attribute_obj.allocationattributeusage.save()

        AllocationUser.objects.create(
            allocation=allocation_obj, user=pi2, status=AllocationUserStatusChoice.objects.get(name="Active")
        )

        # Add university cloud storage
        allocation_obj, _ = Allocation.objects.get_or_create(
            project=project_obj,
            status=AllocationStatusChoice.objects.get(name="Active"),
            start_date=start_date,
            end_date=end_date,
            is_changeable=True,
            justification="Need extra storage for webserver.",
        )

        allocation_attribute_type_obj = AllocationAttributeType.objects.get(name="Cloud Account Name")
        AllocationAttribute.objects.get_or_create(
            allocation_attribute_type=allocation_attribute_type_obj,
            allocation=allocation_obj,
            value="sfoster-openstack",
        )

        allocation_attribute_type_obj = AllocationAttributeType.objects.get(name="Cloud Storage Quota (TB)")
        allocation_attribute_obj, _ = AllocationAttribute.objects.get_or_create(
            allocation_attribute_type=allocation_attribute_type_obj, allocation=allocation_obj, value=20
        )

        allocation_attribute_obj.allocationattributeusage.value = 10
        allocation_attribute_obj.allocationattributeusage.save()

        allocation_attribute_type_obj = AllocationAttributeType.objects.get(name="Cloud Account Name")
        AllocationAttribute.objects.get_or_create(
            allocation_attribute_type=allocation_attribute_type_obj,
            allocation=allocation_obj,
            value="sfoster-openstack",
        )

        allocation_obj.resources.add(Resource.objects.get(name="University Cloud Storage"))
        allocation_obj.save()

        AllocationUser.objects.create(
            allocation=allocation_obj, user=pi2, status=AllocationUserStatusChoice.objects.get(name="Active")
        )

        # Set attributes for resources
        ResourceAttribute.objects.get_or_create(
            resource_attribute_type=ResourceAttributeType.objects.get(name="quantity_default_value"),
            resource=Resource.objects.get(name="University Cloud Storage"),
            value=1,
        )
        ResourceAttribute.objects.get_or_create(
            resource_attribute_type=ResourceAttributeType.objects.get(name="quantity_default_value"),
            resource=Resource.objects.get(name="University Cloud"),
            value=1,
        )
        ResourceAttribute.objects.get_or_create(
            resource_attribute_type=ResourceAttributeType.objects.get(name="quantity_default_value"),
            resource=Resource.objects.get(name="ProjectStorage"),
            value=1,
        )
        ResourceAttribute.objects.get_or_create(
            resource_attribute_type=ResourceAttributeType.objects.get(name="quantity_default_value"),
            resource=Resource.objects.get(name="Budgetstorage"),
            value=10,
        )

        ResourceAttribute.objects.get_or_create(
            resource_attribute_type=ResourceAttributeType.objects.get(name="quantity_label"),
            resource=Resource.objects.get(name="University Cloud Storage"),
            value="Enter storage in 1TB increments",
        )
        ResourceAttribute.objects.get_or_create(
            resource_attribute_type=ResourceAttributeType.objects.get(name="quantity_label"),
            resource=Resource.objects.get(name="University Cloud"),
            value="Enter number of compute allocations to purchase",
        )
        ResourceAttribute.objects.get_or_create(
            resource_attribute_type=ResourceAttributeType.objects.get(name="quantity_label"),
            resource=Resource.objects.get(name="ProjectStorage"),
            value="Enter storage in 1TB increments",
        )
        ResourceAttribute.objects.get_or_create(
            resource_attribute_type=ResourceAttributeType.objects.get(name="quantity_label"),
            resource=Resource.objects.get(name="Budgetstorage"),
            value="Enter storage in 10TB increments (minimum purchase is 10TB)",
        )

        ResourceAttribute.objects.get_or_create(
            resource_attribute_type=ResourceAttributeType.objects.get(name="slurm_cluster"),
            resource=Resource.objects.get(name="Chemistry"),
            value="chemistry",
        )
        ResourceAttribute.objects.get_or_create(
            resource_attribute_type=ResourceAttributeType.objects.get(name="slurm_cluster"),
            resource=Resource.objects.get(name="Physics"),
            value="physics",
        )
        ResourceAttribute.objects.get_or_create(
            resource_attribute_type=ResourceAttributeType.objects.get(name="slurm_cluster"),
            resource=Resource.objects.get(name="Industry"),
            value="industry",
        )
        ResourceAttribute.objects.get_or_create(
            resource_attribute_type=ResourceAttributeType.objects.get(name="slurm_cluster"),
            resource=Resource.objects.get(name="University HPC"),
            value="university-hpc",
        )
        ResourceAttribute.objects.get_or_create(
            resource_attribute_type=ResourceAttributeType.objects.get(name="slurm_cluster"),
            resource=Resource.objects.get(name="University Metered HPC"),
            value="metered-hpc",
        )

        ResourceAttribute.objects.get_or_create(
            resource_attribute_type=ResourceAttributeType.objects.get(name="slurm_specs"),
            resource=Resource.objects.get(name="Chemistry-scavenger"),
            value="QOS+=scavenger:Fairshare=100",
        )
        ResourceAttribute.objects.get_or_create(
            resource_attribute_type=ResourceAttributeType.objects.get(name="slurm_specs"),
            resource=Resource.objects.get(name="Physics-scavenger"),
            value="QOS+=scavenger:Fairshare=100",
        )
        ResourceAttribute.objects.get_or_create(
            resource_attribute_type=ResourceAttributeType.objects.get(name="slurm_specs"),
            resource=Resource.objects.get(name="Industry-scavenger"),
            value="QOS+=scavenger:Fairshare=100",
        )
        ResourceAttribute.objects.get_or_create(
            resource_attribute_type=ResourceAttributeType.objects.get(name="slurm_specs"),
            resource=Resource.objects.get(name="Chemistry-cgray"),
            value="QOS+=cgray:Fairshare=100",
        )
        ResourceAttribute.objects.get_or_create(
            resource_attribute_type=ResourceAttributeType.objects.get(name="slurm_specs"),
            resource=Resource.objects.get(name="Physics-sfoster"),
            value="QOS+=sfoster:Fairshare=100",
        )
        ResourceAttribute.objects.get_or_create(
            resource_attribute_type=ResourceAttributeType.objects.get(name="slurm_specs"),
            resource=Resource.objects.get(name="University Metered HPC"),
            value="GrpTRESMins=cpu={cpumin}",
        )

        # slurm_specs_attrib_list for University Metered HPC
        attriblist_list = [
            "#Set cpumin from Core Usage attribute",
            "cpumin := :Core Usage (Hours)",
            "#Default to 1 SU",
            "cpumin |= 1",
            "#Convert to cpumin",
            "cpumin *= 60",
        ]
        ResourceAttribute.objects.get_or_create(
            resource_attribute_type=ResourceAttributeType.objects.get(name="slurm_specs_attriblist"),
            resource=Resource.objects.get(name="University Metered HPC"),
            value="\n".join(attriblist_list),
        )

        # call_command('loaddata', 'test_data.json')

        # print('All user passwords are set to "test1234", including user "admin".')
