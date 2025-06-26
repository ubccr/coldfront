from django.test import TestCase, Client
from unittest.mock import patch, MagicMock, call

from coldfront.plugins.qumulo.tests.utils.mock_data import (
    create_allocation,
    build_models,
)

from coldfront.core.allocation.signals import (
    allocation_activate,
    allocation_disable,
    allocation_change_approved,
)


def mock_get_attribute(name):
    attribute_dict = {
        "storage_filesystem_path": "foo",
        "storage_export_path": "bar",
        "storage_name": "baz",
        "storage_quota": 7,
        "storage_protocols": '["nfs"]',
    }
    return attribute_dict[name]


@patch("coldfront.plugins.qumulo.signals.QumuloAPI")
class TestSignals(TestCase):
    def setUp(self) -> int:
        self.client = Client()

        build_data = build_models()

        self.project = build_data["project"]
        self.user = build_data["user"]

        self.form_data = {
            "storage_filesystem_path": "foo",
            "storage_export_path": "bar",
            "storage_ticket": "ITSD-54321",
            "storage_name": "baz",
            "storage_quota": 7,
            "protocols": ["nfs"],
            "rw_users": ["test"],
            "ro_users": ["test1"],
            "cost_center": "Uncle Pennybags",
            "billing_exempt": "No",
            "department_number": "Time Travel Services",
            "service_rate": "general",
            "billing_cycle": "monthly",
        }

        self.client.force_login(self.user)

        self.storage_allocation = create_allocation(
            self.project, self.user, self.form_data
        )

    def _createSubAllocation(self):
        sub_form_data = {
            "storage_filesystem_path": "/this/path/should/filter",
            "storage_export_path": "bar",
            "storage_ticket": "ITSD-54321",
            "storage_name": "baz",
            "storage_quota": 4,
            "protocols": ["nfs"],
            "rw_users": ["test"],
            "ro_users": ["test1"],
            "cost_center": "Uncle Pennybags",
            "billing_exempt": "No",
            "department_number": "Time Travel Services",
            "billing_cycle": "monthly",
            "service_rate": "general",
        }

        return create_allocation(
            project=self.project,
            user=self.user,
            form_data=sub_form_data,
            parent=self.storage_allocation,
        )

    @patch("coldfront.plugins.qumulo.signals.async_task")
    def test_allocation_activate_creates_allocation(
        self,
        mock_async_task: MagicMock,
        mock_QumuloAPI: MagicMock,
    ):
        qumulo_instance = mock_QumuloAPI.return_value
        allocation_activate.send(
            sender=self.__class__, allocation_pk=self.storage_allocation.pk
        )

        mock_QumuloAPI.assert_called_once()
        qumulo_instance.create_allocation.assert_called_once_with(
            protocols=["nfs"],
            fs_path=mock_get_attribute("storage_filesystem_path"),
            export_path=mock_get_attribute("storage_export_path"),
            name=mock_get_attribute("storage_name"),
            limit_in_bytes=mock_get_attribute("storage_quota") * (2**40),
        )

    @patch("coldfront.plugins.qumulo.signals.logging.getLogger")
    @patch("coldfront.plugins.qumulo.signals.async_task")
    def test_allocation_activate_handles_missing_attribute_error(
        self,
        mock_async_task: MagicMock,
        mock_getLogger: MagicMock,
        mock_QumuloAPI: MagicMock,
    ):
        qumulo_instance = mock_QumuloAPI.return_value
        qumulo_instance.create_allocation = MagicMock(side_effect=ValueError())

        allocation_activate.send(
            sender=self.__class__, allocation_pk=self.storage_allocation.pk
        )

        mock_QumuloAPI.assert_called_once()
        qumulo_instance.create_allocation.assert_called_once()

        mock_getLogger.return_value.warn.assert_called_once_with(
            "Can't create allocation: Some attributes are missing or invalid"
        )
    
    def test_allocation_change_approved_updates_allocation(
        self,
        mock_QumuloAPI: MagicMock,
    ):
        qumulo_instance = mock_QumuloAPI.return_value

        allocation_change_approved.send(
            sender=self.__class__,
            allocation_pk=self.storage_allocation.pk,
            allocation_change_pk=1,
        )

        byte_limit = mock_get_attribute("storage_quota") * (2**40)
        
        qumulo_instance.update_allocation.assert_called_once_with(
            protocols=["nfs"],
            fs_path=mock_get_attribute("storage_filesystem_path"),
            export_path=mock_get_attribute("storage_export_path"),
            name=mock_get_attribute("storage_name"),
            limit_in_bytes=byte_limit,
        )

    def test_allocation_change_approved_updates_allocation_one_sub_alloc(
        self,
        mock_QumuloAPI: MagicMock,
    ):
        sub_alloc = self._createSubAllocation()
        qumulo_instance = mock_QumuloAPI.return_value

        allocation_change_approved.send(
            sender=self.__class__,
            allocation_pk=self.storage_allocation.pk,
            allocation_change_pk=1,
        )

        byte_limit = mock_get_attribute("storage_quota") * (2**40)
        tb_limit = mock_get_attribute("storage_quota")
        qumulo_instance.update_allocation.assert_called_once_with(
            protocols=["nfs"],
            fs_path=mock_get_attribute("storage_filesystem_path"),
            export_path=mock_get_attribute("storage_export_path"),
            name=mock_get_attribute("storage_name"),
            limit_in_bytes=byte_limit,
        )

        qumulo_instance.update_quota.assert_called_once_with(
                fs_path=sub_alloc.get_attribute(name="storage_filesystem_path"),
                limit_in_bytes=byte_limit,
            )
        self.assertEqual(sub_alloc.get_attribute(name="storage_quota"), tb_limit)

    def test_allocation_change_approved_updates_allocation_multiple_sub_allocs(
        self,
        mock_QumuloAPI: MagicMock,
    ):
        sub_alloc = self._createSubAllocation()
        sub_alloc2 = self._createSubAllocation()
        qumulo_instance = mock_QumuloAPI.return_value

        allocation_change_approved.send(
            sender=self.__class__,
            allocation_pk=self.storage_allocation.pk,
            allocation_change_pk=1,
        )

        byte_limit = mock_get_attribute("storage_quota") * (2**40)
        tb_limit = mock_get_attribute("storage_quota")
        qumulo_instance.update_allocation.assert_called_once_with(
            protocols=["nfs"],
            fs_path=mock_get_attribute("storage_filesystem_path"),
            export_path=mock_get_attribute("storage_export_path"),
            name=mock_get_attribute("storage_name"),
            limit_in_bytes=byte_limit,
        )

        qumulo_instance.update_quota.has_calls(
                call(fs_path=sub_alloc.get_attribute(name="storage_filesystem_path"),
                limit_in_bytes=byte_limit,),
                call(fs_path=sub_alloc2.get_attribute(name="storage_filesystem_path"),
                limit_in_bytes=byte_limit,)
            )
        self.assertEqual(sub_alloc.get_attribute(name="storage_quota"), tb_limit)
        self.assertEqual(sub_alloc2.get_attribute(name="storage_quota"), tb_limit)
        

    def test_allocation_disable_removes_acls(
        self,
        mock_QumuloAPI: MagicMock,
    ):
        qumulo_instance = mock_QumuloAPI.return_value

        with patch(
            "coldfront.plugins.qumulo.signals.AclAllocations.remove_acl_access"
        ) as mock_remove_acl_access:
            allocation_disable.send(
                sender=self.__class__, allocation_pk=self.storage_allocation.pk
            )
            mock_remove_acl_access.assert_called_once_with(self.storage_allocation)
