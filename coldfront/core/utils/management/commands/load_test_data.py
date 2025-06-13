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
from coldfront.core.school.models import School
from coldfront.core.grant.models import Grant, GrantFundingAgency, GrantStatusChoice
from coldfront.core.project.models import (
    Project,
    ProjectStatusChoice,
    ProjectUser,
    ProjectUserRoleChoice,
    ProjectUserStatusChoice,
    ProjectAttribute,
    ProjectAttributeType,
    AttributeType,
)
from coldfront.core.publication.models import Publication, PublicationSource
from coldfront.core.resource.models import (
    Resource,
    ResourceAttribute,
    ResourceAttributeType,
    ResourceType,
)
from coldfront.core.user.management.commands.load_approver_schools import (
    load_approver_schools,
)
from coldfront.core.utils.common import import_from_settings

GENERAL_RESOURCE_NAME = import_from_settings("GENERAL_RESOURCE_NAME")

base_dir = settings.BASE_DIR


# first, last
Users = [
    "Carl	Gray",  # PI#1
    "Stephanie	Foster",  # PI#2
    "Charles	Simmons",  # Director
    "Andrea	Stewart",  # Approver#1
    "Alice	Rivera",  # Approver#2
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


# resource_type, parent_resource, name, description, school, is_available, is_public, is_allocatable
resources = [
    # Generic University Cluster
    (
        "Cluster",
        None,
        GENERAL_RESOURCE_NAME,
        "University Academic Cluster",
        None,
        True,
        True,
        True,
    ),
    # Generic
    (
        "Generic",
        Resource.objects.get(name=GENERAL_RESOURCE_NAME),
        "Tandon",
        "Tandon-wide-resources",
        School.objects.get(description="Tandon School of Engineering"),
        True,
        False,
        True,
    ),  # cgray
    (
        "Generic",
        Resource.objects.get(name=GENERAL_RESOURCE_NAME),
        "Tandon-GPU-Adv",
        "Advanced GPU resource",
        School.objects.get(description="Tandon School of Engineering"),
        True,
        False,
        True,
    ),
    (
        "Generic",
        Resource.objects.get(name=GENERAL_RESOURCE_NAME),
        "CDS",
        "CDS-wide-resources",
        School.objects.get(description="Center for Data Science"),
        True,
        False,
        True,
    ),
    (
        "Generic",
        Resource.objects.get(name=GENERAL_RESOURCE_NAME),
        "CDS-GPU-Prio",
        "Priority GPU resource",
        School.objects.get(description="Center for Data Science"),
        True,
        False,
        True,
    ),  # sfoster
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

        # Approvers
        json_data = {
            "astewart": ["Tandon School of Engineering", "Center for Data Science"],
            "arivera": ["Center for Data Science"],
        }
        load_approver_schools(json_data)

        admin_user, _ = User.objects.get_or_create(username="admin")
        admin_user.is_superuser = True
        admin_user.is_staff = True
        admin_user.save()

        for user in User.objects.all():
            user.set_password("test1234")
            user.save()

        for resource in resources:
            (
                resource_type,
                parent_resource,
                name,
                description,
                school,
                is_available,
                is_public,
                is_allocatable,
            ) = resource
            resource_type_obj = ResourceType.objects.get(name=resource_type)

            Resource.objects.get_or_create(
                resource_type=resource_type_obj,
                parent_resource=parent_resource,
                name=name,
                description=description,
                school=school,
                is_available=is_available,
                is_public=is_public,
                is_allocatable=is_allocatable,
            )

        pi1 = User.objects.get(username="cgray")
        pi1.userprofile.is_pi = True
        pi1.save()
        project_obj, _ = Project.objects.get_or_create(
            pi=pi1,
            title="Angular momentum in QGP holography",
            description="We want to estimate the quark chemical potential of a rotating sample of plasma.",
            school=School.objects.get(description="Tandon School of Engineering"),
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

        publication_source = PublicationSource.objects.get(name="doi")

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

        allocation_obj.resources.add(Resource.objects.get(name="Tandon"))
        allocation_obj.save()

        allocation_attribute_type_obj = AllocationAttributeType.objects.get(
            name="slurm_account_name"
        )
        AllocationAttribute.objects.get_or_create(
            allocation_attribute_type=allocation_attribute_type_obj,
            allocation=allocation_obj,
            value=f"pr_{allocation_obj.project.pk}_Tandon",
        )

        allocation_attribute_type_obj = AllocationAttributeType.objects.get(
            name="slurm_user_specs"
        )
        AllocationAttribute.objects.get_or_create(
            allocation_attribute_type=allocation_attribute_type_obj,
            allocation=allocation_obj,
            value="Fairshare=parent",
        )

        allocation_user_obj = AllocationUser.objects.create(
            allocation=allocation_obj,
            user=pi1,
            status=AllocationUserStatusChoice.objects.get(name="Active"),
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

        allocation_obj.resources.add(Resource.objects.get(name=GENERAL_RESOURCE_NAME))
        allocation_obj.save()

        allocation_attribute_type_obj = AllocationAttributeType.objects.get(
            name="slurm_specs"
        )
        AllocationAttribute.objects.get_or_create(
            allocation_attribute_type=allocation_attribute_type_obj,
            allocation=allocation_obj,
            value="Fairshare=100:QOS+=supporters",
        )

        allocation_attribute_type_obj = AllocationAttributeType.objects.get(
            name="slurm_user_specs"
        )
        AllocationAttribute.objects.get_or_create(
            allocation_attribute_type=allocation_attribute_type_obj,
            allocation=allocation_obj,
            value="Fairshare=parent",
        )

        allocation_attribute_type_obj = AllocationAttributeType.objects.get(
            name="slurm_account_name"
        )
        AllocationAttribute.objects.get_or_create(
            allocation_attribute_type=allocation_attribute_type_obj,
            allocation=allocation_obj,
            value=f"pr_{allocation_obj.project.pk}_general",
        )

        allocation_attribute_type_obj = AllocationAttributeType.objects.get(
            name="SupportersQOS"
        )
        AllocationAttribute.objects.get_or_create(
            allocation_attribute_type=allocation_attribute_type_obj,
            allocation=allocation_obj,
            value="Yes",
        )

        allocation_attribute_type_obj = AllocationAttributeType.objects.get(
            name="SupportersQOSExpireDate"
        )
        AllocationAttribute.objects.get_or_create(
            allocation_attribute_type=allocation_attribute_type_obj,
            allocation=allocation_obj,
            value="2022-01-01",
        )

        allocation_user_obj = AllocationUser.objects.create(
            allocation=allocation_obj,
            user=pi1,
            status=AllocationUserStatusChoice.objects.get(name="Active"),
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

        allocation_obj.resources.add(Resource.objects.get(name="Tandon"))
        allocation_obj.save()

        allocation_attribute_type_obj = AllocationAttributeType.objects.get(
            name="slurm_account_name"
        )
        AllocationAttribute.objects.get_or_create(
            allocation_attribute_type=allocation_attribute_type_obj,
            allocation=allocation_obj,
            value=f"pr_{allocation_obj.project.pk}_Tandon",
        )

        allocation_user_obj = AllocationUser.objects.create(
            allocation=allocation_obj,
            user=pi1,
            status=AllocationUserStatusChoice.objects.get(name="Active"),
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
        allocation_obj.resources.add(Resource.objects.get(name="Tandon"))
        allocation_obj.save()
        allocation_attribute_type_obj = AllocationAttributeType.objects.get(
            name="slurm_account_name"
        )
        AllocationAttribute.objects.get_or_create(
            allocation_attribute_type=allocation_attribute_type_obj,
            allocation=allocation_obj,
            value=f"pr_{allocation_obj.project.pk}_Tandon",
        )
        allocation_attribute_type_obj = AllocationAttributeType.objects.get(
            name="Core Usage (Hours)"
        )
        AllocationAttribute.objects.get_or_create(
            allocation_attribute_type=allocation_attribute_type_obj,
            allocation=allocation_obj,
            value="150000",
        )
        allocation_user_obj = AllocationUser.objects.create(
            allocation=allocation_obj,
            user=pi1,
            status=AllocationUserStatusChoice.objects.get(name="Active"),
        )

        pi2 = User.objects.get(username="sfoster")
        pi2.userprofile.is_pi = True
        pi2.save()
        project_obj, _ = Project.objects.get_or_create(
            pi=pi2,
            title="CDS Project title 1",
            description="This project is for research in Center for Data Science.",
            school=School.objects.get(description="Center for Data Science"),
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
            funding_agency=GrantFundingAgency.objects.get(
                name="Department of Defense (DoD)"
            ),
            grant_start=start_date,
            grant_end=end_date,
            percent_credit=20.0,
            direct_funding=200000,
            total_amount_awarded=1000000,
            status=GrantStatusChoice.objects.get(name="Active"),
        )

        # Add University HPC
        allocation_obj, _ = Allocation.objects.get_or_create(
            project=project_obj,
            status=AllocationStatusChoice.objects.get(name="Active"),
            start_date=start_date,
            end_date=end_date,
            is_changeable=True,
            justification="Need to host my own site.",
        )

        allocation_obj.resources.add(Resource.objects.get(name=GENERAL_RESOURCE_NAME))
        allocation_obj.save()

        allocation_attribute_type_obj = AllocationAttributeType.objects.get(
            name="slurm_account_name"
        )
        AllocationAttribute.objects.get_or_create(
            allocation_attribute_type=allocation_attribute_type_obj,
            allocation=allocation_obj,
            value=f"pr_{allocation_obj.project.pk}_general",
        )

        allocation_attribute_type_obj = AllocationAttributeType.objects.get(
            name="Core Usage (Hours)"
        )
        allocation_attribute_obj, _ = AllocationAttribute.objects.get_or_create(
            allocation_attribute_type=allocation_attribute_type_obj,
            allocation=allocation_obj,
            value=1000,
        )

        allocation_attribute_obj.allocationattributeusage.value = 200
        allocation_attribute_obj.allocationattributeusage.save()

        allocation_user_obj = AllocationUser.objects.create(
            allocation=allocation_obj,
            user=pi2,
            status=AllocationUserStatusChoice.objects.get(name="Active"),
        )
