'''populate Department, DepartmentMemberStatus, DepartmentMember, DepartmentMemberRole'''

import logging

from django.core.management.base import BaseCommand
from ifxuser.models import Organization, OrgRelation, UserAffiliation

from coldfront.plugins.ifx.models import ProjectOrganization
from coldfront.core.department.models import (Department, DepartmentMemberRole,
                                            DepartmentProjects, DepartmentRank,
                                            DepartmentMemberStatus, DepartmentMember)


logger = logging.getLogger('')


class Command(BaseCommand):
    '''
    populate Department records from Organization etc.
    '''
    help = 'populate Department records from Nanites Organization tables. Usage:\n' + \
        './manage.py populate_Department_records'



    def handle(self, *args, **kwargs):
        # Ensure that the department_admin role gets created, determine how to assign that
        # departmentmemberrole to the right departmentmembers.
        # create DepartmentMemberStatus
        for status in ["Active", "Inactive"]:
            DepartmentMemberStatus.objects.get_or_create(name=status)
        # start with only those labs that have a direct or indirect relationship
        # with a lab that's listed as a project.
        child_ids = ProjectOrganization.objects.all().values_list('organization_id', flat=True)
        lab_ids = list(child_ids)
        # collect all organizations that are parent to those organizations in the database
        p_child_ids = {}
        while True:
            orgs = OrgRelation.objects.filter(child_id__in=child_ids)
            # collect parent and child ids
            if orgs:
                for org in orgs:
                    p_child_ids[org.child_id] = org.parent_id
                child_ids = [org.parent_id for org in orgs]
            else:
                break
        # to test, just use those the keys in lab_ids
        lab_dict = {k:v for k,v in p_child_ids.items() if k in lab_ids}
        # new Department for each org in lab_dict values, connected to the labs.
        for lab_id, org_id in lab_dict.items():
            org = Organization.objects.get(id=org_id)
            print(org.name, org.rank, org.id)
            rank = DepartmentRank.objects.get_or_create(name=org.rank)[0]
            # create Department
            department = Department.objects.get_or_create(name=org.name, rank=rank)[0]
            project = ProjectOrganization.objects.get(organization_id=lab_id).project
            # create DepartmentProjects
            DepartmentProjects.objects.get_or_create(department=department, project=project)
            affiliated = UserAffiliation.objects.filter(organization=org)
            for aff_user in affiliated:
                # create DepartmentMemberRoles
                role = DepartmentMemberRole.objects.get_or_create(name=aff_user.role)[0]
                status = "Active" if aff_user.active == 1 else "Inactive"
                # create DepartmentMembers
                DepartmentMember.objects.get_or_create(department=department, member=aff_user.user,
                            role=role, status=DepartmentMemberStatus.objects.get(name=status))
