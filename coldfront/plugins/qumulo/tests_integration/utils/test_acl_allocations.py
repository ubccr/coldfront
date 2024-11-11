from django.test import TestCase, tag

from coldfront.plugins.qumulo.utils.acl_allocations import AclAllocations

from coldfront.core.user.models import User
from coldfront.core.project.models import Project
from coldfront.core.allocation.models import (
    Allocation,
    AllocationAttributeType,
    AllocationAttribute,
)

from coldfront.plugins.qumulo.utils.qumulo_api import QumuloAPI
from coldfront.plugins.qumulo.utils.active_directory_api import ActiveDirectoryAPI
from coldfront.plugins.qumulo.tests.utils.mock_data import build_models


class TestAclAllocations(TestCase):
    def setUp(self) -> None:
        model_data = build_models()

        self.user: User = model_data["user"]
        self.project: Project = model_data["project"]

        self.ad_api = ActiveDirectoryAPI()
        self.test_wustlkey = "test"
        self.user_in_group_filter = (
            lambda group_name: f"(&(objectClass=user)(sAMAccountName={self.test_wustlkey})(memberof=CN={group_name},OU=QA,OU=RIS,OU=Groups,DC=accounts,DC=ad,DC=wustl,DC=edu))"
        )

        return super().setUp()

    @tag("integration")
    def test_create_acl_allocation(self):
        acl_type = "ro"
        test_users = ["test"]

        acl_allocations = AclAllocations(project_pk=self.project)
        acl_allocations.create_acl_allocation(acl_type=acl_type, users=test_users)

        all_allocation_objects = Allocation.objects.all()
        allocation = all_allocation_objects[0]

        group_name = "storage-test-ro"

        self.ad_api.conn.search(
            "dc=accounts,dc=ad,dc=wustl,dc=edu",
            f"(cn={group_name})",
        )
        group_dn = self.ad_api.conn.response[0]["dn"]
        response_group_dn = self.ad_api.get_group_dn(group_name)

        self.assertEqual(response_group_dn, group_dn)

        self.ad_api.delete_ad_group(group_name)

        Allocation.delete(allocation)
        self.assertEqual(len(Allocation.objects.all()), 0)


def clear_acl(path: str, qumulo_api: QumuloAPI):
    acl = {"control": ["PRESENT"], "posix_special_permissions": [], "aces": []}

    return qumulo_api.rc.fs.set_acl_v2(acl=acl, path=path)


def set_allocation_attributes(form_data: dict, allocation):
    allocation_attribute_names = [
        "storage_name",
        "storage_quota",
        "storage_protocols",
        "storage_filesystem_path",
        "storage_export_path",
        "cost_center",
        "department_number",
        "storage_ticket",
        "technical_contact",
        "billing_contact",
        "service_rate",
    ]

    for allocation_attribute_name in allocation_attribute_names:
        allocation_attribute_type = AllocationAttributeType.objects.get(
            name=allocation_attribute_name
        )

        AllocationAttribute.objects.create(
            allocation_attribute_type=allocation_attribute_type,
            allocation=allocation,
            value=form_data.get(allocation_attribute_name),
        )
