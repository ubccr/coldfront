'''populate Department, DepartmentMemberStatus, DepartmentMember, DepartmentMemberRole'''

import logging

from django.core.management.base import BaseCommand
from django.core.exceptions import MultipleObjectsReturned
from ifxuser.models import Organization, OrgRelation, UserAffiliation

from coldfront.plugins.ifx.models import ProjectOrganization
from coldfront.core.department.models import (Department, DepartmentMemberRole,
                                            DepartmentProject, DepartmentRank,
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
        # collect all organizations that are parent to those organizations in the database
        child_parent_ids = {}
        while True:
            orgs = OrgRelation.objects.filter(child_id__in=child_ids)
            print(orgs)
            # collect parent and child ids
            if orgs:
                for org in orgs:
                    child_parent_ids[org.child_id] = org.parent_id
                # replace lab_ids with ids of orgs
                child_ids = [org.parent_id for org in orgs]
            else:
                break
        print(child_parent_ids)
        orgs_added_to_departments = []
        for child_id, parent_id in child_parent_ids.items():
            org = Organization.objects.get(id=parent_id)
            print(org.name, org.rank, org.id)
            rank = DepartmentRank.objects.get_or_create(name=org.rank)[0]
            # create Department
            department = Department.objects.get_or_create(name=org.name, rank=rank)[0]
            orgs_added_to_departments.append(org.id)
            # connect department to subdepartment or to project
            if child_id in orgs_added_to_departments:
                child_dept = Department.objects.get(pk=child_id)
                child_dept.parent = department
                child_dept.save()
            else:
                # if child is project instead of department, link via ProjectOrganization table.
                projects = ProjectOrganization.objects.filter(organization_id=child_id)
                if len(projects) > 1:
                    print("multiples:", projects)
                # multiple projects for the same organization sometimes exist; link them all.
                for project in projects:
                    DepartmentProject.objects.get_or_create(department=department, project_id=project.id)
            affiliated = UserAffiliation.objects.filter(organization=org)
            for aff_user in affiliated:
                # create DepartmentMemberRoles
                role = DepartmentMemberRole.objects.get_or_create(name=aff_user.role)[0]
                status = "Active" if aff_user.active == 1 else "Inactive"
                # create DepartmentMembers
                member, created = DepartmentMember.objects.get_or_create(department=department, member=aff_user.user,
                            role=role, status=DepartmentMemberStatus.objects.get(name=status))
                # after updates to nanites_user_affiliation, should be able to mark
                # as department_admin. The only roles currently in nanites_user_affiliation
                # are pi, lab_manager, member, and PI.
