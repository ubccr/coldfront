from coldfront.core.test_helpers.factories import (
    AAttributeTypeFactory,
    AllocationAttributeTypeFactory,
    AllocationStatusChoiceFactory,
    AllocationUserStatusChoiceFactory,
    FieldOfScienceFactory,
    ProjectAttributeTypeFactory,
    ProjectStatusChoiceFactory,
    ProjectUserRoleChoiceFactory,
    ProjectUserStatusChoiceFactory,
    PAttributeTypeFactory,
    ResourceFactory,
)

from coldfront.core.test_helpers.factories import field_of_science_provider


def create_allocation_assets() -> None:
    field_of_science_provider.add_element("Other")
    FieldOfScienceFactory(description="Other")
    ProjectStatusChoiceFactory(name="New")
    ProjectUserRoleChoiceFactory(name="Manager")
    ProjectUserStatusChoiceFactory(name="Active")
    AllocationStatusChoiceFactory(name="Pending")
    AllocationUserStatusChoiceFactory(name="Active")
    allocation_attribute_names = [
        ("storage_name", "Text"),
        ("storage_ticket", "Text"),
        ("storage_quota", "Int"),
        ("storage_protocols", "Text"),
        ("storage_filesystem_path", "Text"),
        ("storage_export_path", "Text"),
        ("cost_center", "Text"),
        ("department_number", "Text"),
        ("technical_contact", "Text"),
        ("billing_contact", "Text"),
        ("service_rate", "Text"),
        ("storage_acl_name", "Text"),
        ("storage_allocation_pk", "Int"),
        ("secure", "Yes/No"),
        ("audit", "Yes/No"),
        ("billing_startdate", "Date"),
        ("sponsor_department_number", "Text"),
        ("fileset_name", "Text"),
        ("fileset_alias", "Text"),
        ("billing_exempt", "Yes/No"),
        ("itsm_comment", "JSON"),
        ("billing_cycle", "Text"),
        ("subsidized", "Yes/No"),
        ("allow_nonfaculty", "Yes/No"),
        ("sla_name", "Text"),
        ("prepaid_time", "Int"),
        ("prepaid_billing_date", "Date"),
    ]
    for (
        allocation_attribute_name,
        allocation_attribute_type,
    ) in allocation_attribute_names:

        AllocationAttributeTypeFactory(
            name=allocation_attribute_name,
            attribute_type=AAttributeTypeFactory(name=allocation_attribute_type),
        )

    project_attribute_names = [
        ("is_condo_group", "Yes/No"),
        ("sponsor_department_number", "Text"),
        ("allow_nonfaculty", "Yes/No"),
    ]
    for project_attribute_name, project_attribute_type in project_attribute_names:
        ProjectAttributeTypeFactory(
            name=project_attribute_name,
            attribute_type=PAttributeTypeFactory(name=project_attribute_type),
        )

    ResourceFactory(name="Storage2")
    ResourceFactory(name="rw")
    ResourceFactory(name="ro")
