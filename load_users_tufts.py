from coldfront.core.project.models import (Project, ProjectStatusChoice, 
                                           ProjectUser, ProjectUserRoleChoice,
                                           ProjectUserStatusChoice, ProjectAttribute,
                                           ProjectAttributeType, AttributeType)
from coldfront.core.allocation.models import (Allocation, AllocationAttribute,
                                              AllocationAttributeType,
                                              AllocationStatusChoice,
                                              AllocationUser,
                                              AllocationUserStatusChoice)
from coldfront.core.field_of_science.models import FieldOfScience


from django.contrib.auth.models import User



def load_users(user_list):

    for user in user_list:
        first_name, last_name = user.split()
        username = first_name[0].lower()+last_name.lower().strip()
        email = username + '@example.com'
        User.objects.get_or_create(
            first_name=first_name.strip(),
            last_name=last_name.strip(),
            username=username.strip(),
            email=email.strip()
        )


def set_pi(username):
    pi1 = User.objects.get(username=username)
    pi1.userprofile.is_pi = True
    pi1.save()


def create_project(pi, title, description, field_of_science):
    project_obj, _ = Project.objects.get_or_create(
    pi=pi,
    title=title,
    description=description,
    field_of_science=FieldOfScience.objects.get(
        description=field_of_science),
    status=ProjectStatusChoice.objects.get(name='Active'),
    force_review=True)

    project_pi_obj, _ = ProjectUser.objects.get_or_create(
        user=pi,
        project=project_obj,
        role=ProjectUserRoleChoice.objects.get(name='Manager'),
        status=ProjectUserStatusChoice.objects.get(name='Active'))
    
    return project_obj

def allocate_hpc_account(project_obj, start_date, end_date):    
    # Add hpc account
    allocation_obj, _ = Allocation.objects.get_or_create(
        project=project_obj,
        status=AllocationStatusChoice.objects.get(name='Active'),
        start_date=start_date,
        end_date=end_date,
        is_changeable=True,
        justification='Need access to HPC compute.'
    )

    allocation_attribute_type_obj = AllocationAttributeType.objects.get(
        name='Cloud Account Name')
    AllocationAttribute.objects.get_or_create(
        allocation_attribute_type=allocation_attribute_type_obj,
        allocation=allocation_obj,
        value='sfoster-openstack')

    allocation_attribute_type_obj = AllocationAttributeType.objects.get(
        name='Cloud Storage Quota (TB)')
    allocation_attribute_obj, _ = AllocationAttribute.objects.get_or_create(
        allocation_attribute_type=allocation_attribute_type_obj,
        allocation=allocation_obj,
        value=20)

    allocation_attribute_obj.allocationattributeusage.value = 10
    allocation_attribute_obj.allocationattributeusage.save()

    allocation_attribute_type_obj = AllocationAttributeType.objects.get(
        name='Cloud Account Name')
    
    AllocationAttribute.objects.get_or_create(
        allocation_attribute_type=allocation_attribute_type_obj,
        allocation=allocation_obj,
        value='sfoster-openstack')

    allocation_obj.resources.add(
        Resource.objects.get(name='University Cloud Storage'))
    allocation_obj.save()

    allocation_user_obj = AllocationUser.objects.create(
        allocation=allocation_obj,
        user=pi2,
        status=AllocationUserStatusChoice.objects.get(name='Active')
    )