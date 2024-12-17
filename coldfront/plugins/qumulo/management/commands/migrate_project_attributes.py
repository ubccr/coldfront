from coldfront.core.project.models import (
    ProjectAttributeType,
    AttributeType,
    Project,
    ProjectAttribute,
)
from django.core.management.base import BaseCommand

from django.db.models import OuterRef, Subquery


class Command(BaseCommand):
    def handle(self, *args, **options):
        print("Updating Qumulo Project Attributes")
        # updating required project attributes for all projects

        # for sponsor_department_number, use ""
        self._migrate_project_attribute("sponsor_department_number", "")
        self._migrate_project_attribute("is_condo_group", "No")

    def _migrate_project_attribute(self, attribute_name, default_value):
        attribute_type = ProjectAttributeType.objects.get(name=attribute_name)
        attribute_sub_q = ProjectAttribute.objects.filter(
            project=OuterRef("pk"), proj_attr_type=attribute_type
        ).values("value")[:1]

        # find all projects
        all_projects = Project.objects.all()
        all_projects = all_projects.annotate(
            **{attribute_name: Subquery(attribute_sub_q)}
        )

        for project in all_projects:
            ProjectAttribute.objects.get_or_create(
                proj_attr_type=attribute_type, project=project, value=default_value
            )
