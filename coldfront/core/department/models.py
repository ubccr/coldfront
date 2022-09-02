from django.db import models
from ifxuser.models import Organization, OrgRelation, UserAffiliation

from coldfront.core.project.models import Project
from coldfront.plugins.ifx.models import ProjectOrganization


class DepartmentSelector(models.Manager):
    def get_queryset(self):
        """
        collect non-lab Organization objects that are directly or indirectly linked
        to labs that are Coldfront projects.
        """
        # get organization ids for all projects
        child_id_search_list = set(ProjectOrganization.objects.all().values_list('organization_id'))
        child_parent_ids = {}
        while True:
            # collect all parents of organizations in child_id_search_list
            orgrelations = OrgRelation.objects.filter(child_id__in=child_id_search_list)
            # collect parent and child ids
            if orgrelations:
                for relation in orgrelations:
                    child_parent_ids[relation.child_id] = relation.parent_id
                # replace child_ids with ids of orgs
                child_id_search_list = {relation.parent_id for relation in orgrelations}
            else:
                break
        dept_ids = set(parent_id for parent_id in child_parent_ids.values())
        return super().get_queryset().filter(id__in=dept_ids)


class Department(Organization):
    """
    All entities in nanites_organization where rank != lab and entity connects to
    a Project object.
    """
    objects = DepartmentSelector()


    class Meta:
        proxy = True


    def get_projects(self):
        """Get all projects related to the Department, either directly or indirectly.
        """
        parent_search_ids = OrgRelation.objects.filter(parent=self).values_list(
                                                            'child_id', flat=True)
        lab_search_ids = list(parent_search_ids)
        while True:
            children_links = OrgRelation.objects.filter(parent_id__in=parent_search_ids)
            if children_links:
                parent_search_ids = [link.child_id for link in children_links]
                lab_search_ids.extend(children_links.filter(child__rank="lab").values_list(
                                                            'child_id', flat=True))
            else:
                project_org_links = ProjectOrganization.objects.filter(
                                organization_id__in=lab_search_ids).values_list("project_id")
                return Project.objects.filter(pk__in=project_org_links)

    @property
    def biller(self):
        return False
        # return self.role

    @property
    def members(self):
        return UserAffiliation.objects.filter(organization=self)

    @property
    def projects(self):
        return self.get_projects()

    @property
    def project_count(self):
        return len(self.get_projects())



class DepartmentProjectManager(models.Manager):
    def get_queryset(self):
        """collect department members using Department and UserAffiliation"""
        project_org_links = []
        for department in Department.objects.all():
            parent_search_ids = OrgRelation.objects.filter(parent=department).values_list(
                                                                'child_id', flat=True)
            lab_search_ids = list(parent_search_ids)
            while True:
                children_links = OrgRelation.objects.filter(parent_id__in=parent_search_ids)
                if children_links:
                    parent_search_ids = [link.child_id for link in children_links]
                    lab_search_ids.extend(list(children_links.filter(
                            child__rank="lab").values_list('child_id', flat=True)))
                else:
                    project_org_links.extend(ProjectOrganization.objects.filter(
                        organization_id__in=lab_search_ids).values_list("project_id", flat=True))
                    break
        return super().get_queryset().filter(pk__in=project_org_links)


class DepartmentProject(ProjectOrganization):
    objects = DepartmentProjectManager()

    class Meta:
        proxy = True

    @property
    def department(self):
        return self.organization


class DepartmentMemberManager(models.Manager):
    def get_queryset(self):
        """collect department members using Department and UserAffiliation"""
        departments = Department.objects.all()
        return super().get_queryset().filter(organization__in=departments)


class DepartmentMember(UserAffiliation):
    """subset of UserAffiliation records that are related to Department records.
    """
    objects = DepartmentMemberManager()

    class Meta:
        proxy = True

    @property
    def member(self):
        return self.user

    @property
    def status(self):
        return "Active" if self.active == 1 else "Inactive"

    @property
    def department(self):
        return self.organization
