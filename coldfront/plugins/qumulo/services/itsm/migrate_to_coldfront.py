from coldfront.core.field_of_science.models import FieldOfScience

from coldfront.plugins.qumulo.services.allocation_service import AllocationService

from coldfront.core.allocation.models import (
    Allocation,
    AllocationAttribute,
    AllocationAttributeType,
    Project,
    User,
)

from coldfront.core.project.models import (
    Project,
    ProjectAttribute,
    ProjectAttributeType,
    ProjectStatusChoice,
    ProjectUser,
    ProjectUserRoleChoice,
    ProjectUserStatusChoice,
)

from coldfront.plugins.qumulo.services.itsm.itsm_client import ItsmClient

from coldfront.plugins.qumulo.services.itsm.fields.itsm_to_coldfront_fields_factory import (
    ItsmToColdfrontFieldsFactory,
)


class MigrateToColdfront:

    def by_fileset_alias(self, fileset_alias: str) -> str:
        itsm_result = self.__get_itsm_allocation_by_fileset_alias(fileset_alias)
        result = self.__create_by(fileset_alias, itsm_result)
        return result

    def by_fileset_name(self, fileset_name: str) -> str:
        itsm_result = self.__get_itsm_allocation_by_fileset_name(fileset_name)
        result = self.__create_by(fileset_name, itsm_result)
        return result

    # Private Methods
    def __create_by(self, fileset_key: str, itsm_result: str) -> str:
        self.__validate_itsm_result_set(fileset_key, itsm_result)
        itsm_allocation = itsm_result[0]
        fields = ItsmToColdfrontFieldsFactory.get_fields(itsm_allocation)

        field_error_messages = {}
        for field in fields:
            validation_messages = field.validate()
            if validation_messages:
                if not field.itsm_attribute_name in field_error_messages:
                    field_error_messages[field.itsm_attribute_name] = []

                field_error_messages[field.itsm_attribute_name] += validation_messages

        if field_error_messages:
            errors = {"errors": field_error_messages}
            raise Exception("Validation messages: ", errors)

        pi_user = self.__get_or_create_user(fields)
        project, created = self.__get_or_create_project(pi_user)
        if created:
            self.__create_project_user(project, pi_user)
            self.__create_project_attributes(fields, project)
        allocation = self.__create_allocation(fields, project, pi_user)
        self.__create_allocation_attributes(fields, allocation)
        return {
            "allocation_id": allocation.id,
            "project_id": project.id,
            "pi_user_id": pi_user.id,
        }

    def __get_itsm_allocation_by_fileset_name(self, fileset_name: str) -> str:
        itsm_client = ItsmClient()
        itsm_allocation = itsm_client.get_fs1_allocation_by_fileset_name(fileset_name)
        return itsm_allocation

    def __get_itsm_allocation_by_fileset_alias(self, fileset_alias: str) -> list:
        itsm_client = ItsmClient()
        itsm_allocation = itsm_client.get_fs1_allocation_by_fileset_alias(fileset_alias)
        return itsm_allocation

    def __validate_itsm_result_set(self, fileset_key: str, itsm_result: list) -> bool:
        how_many = len(itsm_result)
        # ITSM does not return a respond code of 404 when the service provision record is not found.
        # Instead, it returns an empty array.
        if how_many == 0:
            raise Exception(f"ITSM active allocation was not found for {fileset_key}")

        if how_many > 1:
            raise Exception(
                f"Multiple ({how_many} total) ITSM active allocations were found for {fileset_key}"
            )

        return True

    def __get_or_create_user(self, fields: list) -> User:
        username = self.__get_username(fields)
        user, _ = User.objects.get_or_create(
            username=username,
            email=f"{username}@wustl.edu",
        )
        return user

    def __get_or_create_project(self, pi_user: User) -> Project:
        project_query = Project.objects.filter(
            title=pi_user.username,
            pi=pi_user,
        )
        if project_query.exists():
            return (project_query[0], False)

        description = f"project for {pi_user.username}"
        title = pi_user.username
        field_of_science = FieldOfScience.objects.get(description="Other")
        new_status = ProjectStatusChoice.objects.get(name="New")

        project = Project.objects.create(
            field_of_science=field_of_science,
            title=title,
            pi=pi_user,
            description=description,
            status=new_status,
            force_review=False,
            requires_review=False,
        )
        return (project, True)

    def __create_project_user(self, project: Project, pi_user: User) -> ProjectUser:
        pi_role = ProjectUserRoleChoice.objects.get(name="Manager")
        user_status = ProjectUserStatusChoice.objects.get(name="Active")

        project_user = ProjectUser.objects.create(
            user=pi_user,
            project=project,
            role=pi_role,
            status=user_status,
        )
        return project_user

    def __create_project_attributes(self, fields: list, project: Project) -> None:
        project_attributes = filter(
            lambda field: field.entity == "project_attribute"
            and field.value is not None,
            fields,
        )
        for field in list(project_attributes):
            for attribute in field.attributes:
                if attribute["name"] == "proj_attr_type":
                    project_attribute_type = ProjectAttributeType.objects.get(
                        name=attribute["value"]
                    )
                    ProjectAttribute.objects.get_or_create(
                        proj_attr_type=project_attribute_type,
                        project=project,
                        value=field.value,
                    )

    def __create_allocation(self, fields: list, project: Project, pi_user: User) -> str:
        attributes_for_allocation = filter(
            lambda field: field.entity == "allocation_form", fields
        )

        allocation_data = {}
        allocation_data["project_pk"] = project.id
        allocation_data["ro_users"] = []
        for field in list(attributes_for_allocation):
            allocation_data.update(field.entity_item)

        service_result = AllocationService.create_new_allocation(
            allocation_data, pi_user
        )
        return service_result["allocation"]

    def __create_allocation_attributes(
        self, fields: list, allocation: Allocation
    ) -> None:
        allocation_attributes = filter(
            lambda field: field.entity == "allocation_attribute"
            and field.value is not None,
            fields,
        )

        for field in list(allocation_attributes):
            for attribute in field.attributes:
                if attribute["name"] == "allocation_attribute_type__name":
                    allocation_attribute_type = AllocationAttributeType.objects.get(
                        name=attribute["value"]
                    )
                    AllocationAttribute.objects.update_or_create(
                        allocation_attribute_type=allocation_attribute_type,
                        allocation=allocation,
                        defaults={"value": field.value},
                    )

    def __get_username(self, fields: list) -> str:
        for field in fields:
            username = field.get_username()
            if username is not None:
                return username

        return None
