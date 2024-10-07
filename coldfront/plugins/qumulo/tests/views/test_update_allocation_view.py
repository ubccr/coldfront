from django.contrib import messages
from django.test import Client, RequestFactory, TestCase
from unittest.mock import patch, call, MagicMock

from coldfront.core.allocation.models import Allocation, AllocationUser

from coldfront.plugins.qumulo.forms import UpdateAllocationForm
from coldfront.plugins.qumulo.hooks import acl_reset_complete_hook
from coldfront.plugins.qumulo.tasks import reset_allocation_acls
from coldfront.plugins.qumulo.views.update_allocation_view import (
    UpdateAllocationView
)
from coldfront.plugins.qumulo.tests.utils.mock_data import (
    create_allocation,
    build_models,
)
from coldfront.plugins.qumulo.utils.acl_allocations import AclAllocations

from coldfront.core.allocation.models import (
    AllocationAttribute,
    AllocationAttributeChangeRequest,
    AllocationAttributeType,
    AllocationChangeRequest,
    AllocationChangeStatusChoice,
    AllocationLinkage,
)
@patch("coldfront.plugins.qumulo.views.update_allocation_view.ActiveDirectoryAPI")
class UpdateAllocationViewTests(TestCase):
    def setUp(self):
        self.client = Client()

        build_data = build_models()

        self.project = build_data["project"]
        self.user = build_data["user"]

        self.client.force_login(self.user)

        self.request = RequestFactory().get('/request/path/does/not/matter/')
        self.request.user = self.user

        self.form_data = {
            "storage_filesystem_path": "foo",
            "storage_export_path": "bar",
            "storage_ticket": "ITSD-54321",
            "storage_name": "baz",
            "storage_quota": 7,
            "protocols": ["nfs"],
            "rw_users": ["test"],
            "ro_users": [],
            "cost_center": "Uncle Pennybags",
            "department_number": "Time Travel Services",
            "service_rate": "consumption",
            "technical_contact": "it.guru",
            "billing_contact": "finance.guru",
        }

        self.storage_allocation = create_allocation(
            self.project, self.user, self.form_data
        )

    def test_get_access_users_returns_one_user(
        self, mock_ActiveDirectoryAPI: MagicMock
    ):
        form_data = {
            "storage_filesystem_path": "foo",
            "storage_export_path": "bar",
            "storage_ticket": "ITSD-54321",
            "storage_name": "baz",
            "storage_quota": 7,
            "protocols": ["nfs"],
            "rw_users": ["test"],
            "ro_users": [],
            "cost_center": "Uncle Pennybags",
            "department_number": "Time Travel Services",
            "service_rate": "consumption",
        }

        storage_allocation = create_allocation(self.project, self.user, form_data)

        access_users = UpdateAllocationView.get_access_users("rw", storage_allocation)

        self.assertCountEqual(access_users, form_data["rw_users"])

    def test_get_access_users_returns_multiple_users(
        self, mock_ActiveDirectoryAPI: MagicMock
    ):
        form_data = {
            "storage_filesystem_path": "foo",
            "storage_export_path": "bar",
            "storage_ticket": "ITSD-54321",
            "storage_name": "baz",
            "storage_quota": 7,
            "protocols": ["nfs"],
            "rw_users": ["test", "foo", "bar"],
            "ro_users": [],
            "cost_center": "Uncle Pennybags",
            "department_number": "Time Travel Services",
            "service_rate": "consumption",
        }

        storage_allocation = create_allocation(self.project, self.user, form_data)

        access_users = UpdateAllocationView.get_access_users("rw", storage_allocation)

        self.assertCountEqual(access_users, form_data["rw_users"])

    def test_get_access_users_returns_no_users(
        self, mock_ActiveDirectoryAPI: MagicMock
    ):
        form_data = {
            "storage_filesystem_path": "foo",
            "storage_export_path": "bar",
            "storage_ticket": "ITSD-54321",
            "storage_name": "baz",
            "storage_quota": 7,
            "protocols": ["nfs"],
            "rw_users": ["test", "foo", "bar"],
            "ro_users": [],
            "cost_center": "Uncle Pennybags",
            "department_number": "Time Travel Services",
            "service_rate": "consumption",
        }

        storage_allocation = create_allocation(self.project, self.user, form_data)

        access_users = UpdateAllocationView.get_access_users("ro", storage_allocation)

        self.assertCountEqual(access_users, form_data["ro_users"])

    def test_set_access_users_ignores_unchanged(
        self, mock_ActiveDirectoryAPI: MagicMock
    ):

        form_data = {
            "storage_filesystem_path": "foo",
            "storage_export_path": "bar",
            "storage_ticket": "ITSD-54321",
            "storage_name": "baz",
            "storage_quota": 7,
            "protocols": ["nfs"],
            "rw_users": ["test", "foo", "bar"],
            "ro_users": [],
            "cost_center": "Uncle Pennybags",
            "department_number": "Time Travel Services",
            "service_rate": "consumption",
        }

        storage_allocation = create_allocation(self.project, self.user, form_data)

        with patch(
            "coldfront.plugins.qumulo.views.update_allocation_view.AclAllocations.add_user_to_access_allocation",
        ) as mock_add_user_to_access_allocation:
            UpdateAllocationView.set_access_users(
                "rw", form_data["rw_users"], storage_allocation
            )

            mock_add_user_to_access_allocation.assert_not_called()

    def test_set_access_users_adds_new_user(self, mock_ActiveDirectoryAPI: MagicMock):
        form_data = {
            "storage_filesystem_path": "foo",
            "storage_export_path": "bar",
            "storage_ticket": "ITSD-54321",
            "storage_name": "baz",
            "storage_quota": 7,
            "protocols": ["nfs"],
            "rw_users": ["test", "foo", "bar"],
            "ro_users": [],
            "cost_center": "Uncle Pennybags",
            "department_number": "Time Travel Services",
            "service_rate": "consumption",
        }

        storage_allocation = create_allocation(self.project, self.user, form_data)

        new_rw_users: list = form_data["rw_users"].copy()
        new_rw_users.append("baz")

        with patch(
            "coldfront.plugins.qumulo.views.update_allocation_view.AclAllocations.add_user_to_access_allocation",
        ) as mock_add_user_to_access_allocation:
            UpdateAllocationView.set_access_users(
                "rw", new_rw_users, storage_allocation
            )

            access_allocation = AclAllocations.get_access_allocation(
                storage_allocation, "rw"
            )

            mock_add_user_to_access_allocation.assert_called_once_with(
                "baz", access_allocation
            )

    def test_set_access_users_adds_new_users(self, mock_ActiveDirectoryAPI: MagicMock):
        form_data = {
            "storage_filesystem_path": "foo",
            "storage_export_path": "bar",
            "storage_ticket": "ITSD-54321",
            "storage_name": "baz",
            "storage_quota": 7,
            "protocols": ["nfs"],
            "rw_users": ["test", "foo", "bar"],
            "ro_users": [],
            "cost_center": "Uncle Pennybags",
            "department_number": "Time Travel Services",
            "service_rate": "consumption",
        }

        with patch(
            "coldfront.plugins.qumulo.signals.update_user_with_additional_data"
        ) as mock_update:
            storage_allocation = create_allocation(self.project, self.user, form_data)
            update_calls = [
                call("foo"),
                call("bar"),
            ]
            mock_update.assert_has_calls(update_calls)
            assert mock_update.call_count == 2

        extra_users = ["baz", "bah"]
        new_rw_users: list = form_data["rw_users"].copy() + extra_users

        with patch(
            "coldfront.plugins.qumulo.views.update_allocation_view.AclAllocations.add_user_to_access_allocation",
        ) as mock_add_user_to_access_allocation:
            UpdateAllocationView.set_access_users(
                "rw", new_rw_users, storage_allocation
            )

            access_allocation = AclAllocations.get_access_allocation(
                storage_allocation, "rw"
            )

            calls = []
            for user in extra_users:
                calls.append(call(user, access_allocation))

            mock_add_user_to_access_allocation.assert_has_calls(calls)

    def test_set_access_users_removes_user(self, mock_ActiveDirectoryAPI: MagicMock):
        form_data = {
            "storage_filesystem_path": "foo",
            "storage_export_path": "bar",
            "storage_ticket": "ITSD-54321",
            "storage_name": "baz",
            "storage_quota": 7,
            "protocols": ["nfs"],
            "rw_users": ["test", "foo", "bar"],
            "ro_users": [],
            "cost_center": "Uncle Pennybags",
            "department_number": "Time Travel Services",
            "service_rate": "consumption",
        }

        storage_allocation = create_allocation(self.project, self.user, form_data)

        new_rw_users: list = form_data["rw_users"].copy()
        new_rw_users.remove("test")

        UpdateAllocationView.set_access_users("rw", new_rw_users, storage_allocation)

        access_allocation = AclAllocations.get_access_allocation(
            storage_allocation, "rw"
        )
        access_allocation_users = AllocationUser.objects.filter(
            allocation=access_allocation
        )
        access_usernames = [
            allocation_user.user.username for allocation_user in access_allocation_users
        ]

        self.assertNotIn("test", access_usernames)

    def test_set_access_users_adds_user_to_ad(self, mock_ActiveDirectoryAPI: MagicMock):
        mock_active_directory_api = mock_ActiveDirectoryAPI.return_value

        form_data = {
            "storage_filesystem_path": "foo",
            "storage_export_path": "bar",
            "storage_ticket": "ITSD-54321",
            "storage_name": "baz",
            "storage_quota": 7,
            "protocols": ["nfs"],
            "rw_users": ["test", "foo", "bar"],
            "ro_users": [],
            "cost_center": "Uncle Pennybags",
            "department_number": "Time Travel Services",
            "service_rate": "consumption",
        }

        storage_allocation = create_allocation(self.project, self.user, form_data)

        new_rw_users: list = form_data["rw_users"].copy()
        new_rw_users.append("baz")

        UpdateAllocationView.set_access_users("rw", new_rw_users, storage_allocation)

        access_allocation = AclAllocations.get_access_allocation(
            storage_allocation, "rw"
        )

        mock_active_directory_api.add_user_to_ad_group.assert_called_once_with(
            "baz", access_allocation.get_attribute("storage_acl_name")
        )

    def test_set_access_users_removes_user(self, mock_ActiveDirectoryAPI: MagicMock):
        mock_active_directory_api = mock_ActiveDirectoryAPI.return_value

        form_data = {
            "storage_filesystem_path": "foo",
            "storage_export_path": "bar",
            "storage_ticket": "ITSD-54321",
            "storage_name": "baz",
            "storage_quota": 7,
            "protocols": ["nfs"],
            "rw_users": ["test", "foo", "bar"],
            "ro_users": [],
            "cost_center": "Uncle Pennybags",
            "department_number": "Time Travel Services",
            "service_rate": "consumption",
        }

        storage_allocation = create_allocation(self.project, self.user, form_data)

        new_rw_users: list = form_data["rw_users"].copy()
        new_rw_users.remove("test")

        UpdateAllocationView.set_access_users("rw", new_rw_users, storage_allocation)

        access_allocation = AclAllocations.get_access_allocation(
            storage_allocation, "rw"
        )

        mock_active_directory_api.remove_user_from_group.assert_called_once_with(
            "test", access_allocation.get_attribute("storage_acl_name")
        )

    def test_attribute_change_request_creation(
        self, mock_ActiveDirectoryAPI: MagicMock
    ):
        # allocation and allocation attributes already created

        # need to create an allocation change request

        # an allocation attribute, and an allocation change request

        allocation_change_request = AllocationChangeRequest.objects.create(
            allocation=self.storage_allocation,
            status=AllocationChangeStatusChoice.objects.get(name="Pending"),
            justification="updating",
            notes="updating",
            end_date_extension=10,
        )

        # NOTE - "storage_protocols" will have special handling
        attributes_to_check = [
            "cost_center",
            "department_number",
            "technical_contact",
            "billing_contact",
            "service_rate",
            "storage_ticket",
            "storage_quota",
        ]

        original_values = [
            AllocationAttribute.objects.get(
                allocation_attribute_type=AllocationAttributeType.objects.get(
                    name=attr_name
                ),
                allocation=self.storage_allocation,
            ).value
            for attr_name in attributes_to_check
        ]

        for attr, val in zip(attributes_to_check, original_values):
            # without mutation, confirm that *no* allocation change requests are created
            UpdateAllocationView._handle_attribute_change(
                allocation=self.storage_allocation,
                allocation_change_request=allocation_change_request,
                attribute_name=attr,
                form_value=val,
            )
            self.assertEqual(len(AllocationAttributeChangeRequest.objects.all()), 0)

        # now, try mutating the values

        for attr, val in zip(attributes_to_check, original_values):
            if attr == "storage_quota":
                new_val = str(int(val) + 10)
            else:
                new_val = val + "MUTATE"

            UpdateAllocationView._handle_attribute_change(
                allocation=self.storage_allocation,
                allocation_change_request=allocation_change_request,
                attribute_name=attr,
                form_value=new_val,
            )

            change_request = AllocationAttributeChangeRequest.objects.get(
                allocation_attribute=AllocationAttribute.objects.get(
                    allocation_attribute_type=AllocationAttributeType.objects.get(
                        name=attr
                    ),
                    allocation=self.storage_allocation,
                ),
                allocation_change_request=allocation_change_request,
            )

            self.assertEqual(change_request.new_value, new_val)

    def test_update_allocation_form_and_view_valid(
        self, mock_ActiveDirectoryAPI: MagicMock
    ):
        response = UpdateAllocationView.as_view()(self.request, allocation_id=1)
        self.assertEqual(response.status_code, 200)

    def test_context_data_no_linkage(
        self, mock_ActiveDirectoryAPI: MagicMock
    ):
        view = UpdateAllocationView(
            form=UpdateAllocationForm(data=self.form_data, user_id=self.user.id)
        )
        view.setup(self.request, allocation_id=1)
        self.assertFalse(
            dict(view.get_context_data()).get('allocation_has_children', True)
        )

    def test_context_data_with_linked_sub(
        self, mock_ActiveDirectoryAPI: MagicMock
    ):
        sub_form_data = {
            "storage_filesystem_path": "foo",
            "storage_export_path": "bar",
            "storage_ticket": "ITSD-54321",
            "storage_name": "baz",
            "storage_quota": 7,
            "protocols": ["nfs"],
            "rw_users": ["test"],
            "ro_users": [],
            "cost_center": "Uncle Pennybags",
            "department_number": "Time Travel Services",
            "service_rate": "consumption",
            "technical_contact": "it.guru",
            "billing_contact": "finance.guru",
        }
        sub_allocation = create_allocation(
            self.project, self.user, sub_form_data, self.storage_allocation
        )
        view = UpdateAllocationView(
            form=UpdateAllocationForm(data=self.form_data, user_id=self.user.id)
        )
        view.setup(self.request, allocation_id=1)
        self.assertTrue(
            dict(view.get_context_data()).get('allocation_has_children', True)
        )

    def test_valid_form_with_reset_acls_calls_reset_acls(
        self, mock_ActiveDirectoryAPI: MagicMock
    ):
        request = RequestFactory().post('/irrelevant', {'reset_acls': 'set'})
        request.user = self.user
        form=UpdateAllocationForm(data=self.form_data, user_id=self.user.id)
        form.cleaned_data = {
            'protocols': ['smb'],
            'storage_export_path': 'bar',
            'storage_ticket': 'ITSD-12345',
            'storage_filesystem_path': '/storage2-dev/fs1/allocationName'
        }
        form.clean()
        view = UpdateAllocationView(form=form, user_id=self.user.id)
        view.setup(request, allocation_id=1)
        view.success_id = 1
        view._reset_acls = MagicMock()
        view._updated_fields_handler = MagicMock()
        self.assertTrue(view.form_valid(form))
        view._reset_acls.assert_called_once()
        view._updated_fields_handler.assert_not_called()

    def test_reset_acls_runs_task_with_valid_args(
        self, mock_ActiveDirectoryAPI: MagicMock
    ):
        for onOff, trueFalse in {'on': True, 'off': False}.items():
            messages.add_message = MagicMock()
            request = RequestFactory() \
                .post(
                    '/irrelevant',
                    {
                        'reset_acls': 'set',
                        'reset_sub_acls': 'on' if onOff == 'on' else ''
                    }
                )
            request.user = self.user
            form=UpdateAllocationForm(data=self.form_data, user_id=self.user.id)
            form.cleaned_data = {
                'project_pk': self.project.id,
                'protocols': ['smb'],
                "rw_users": ["test"],
                "ro_users": ["test2"],
                'storage_export_path': 'bar',
                'storage_filesystem_path': 'updatedFormPath',
                'storage_name': 'foo',
                'storage_ticket': 'ITSD-12345'
            }
            form.clean()
            view = UpdateAllocationView(form=form, user_id=self.user.id)
            view.setup(request, allocation_id=1)
            view.success_id = 1
    # /Users/brennanmulligan/repos/consolidate/coldfront-wustl-fork/coldfront/plugins/qumulo/utils/acl_allocations.py
            with patch(
                    (
                        "coldfront.plugins.qumulo.views.update_allocation_view."
                        "async_task"
                    )
                ) as mock_async_task, patch(
                    (
                        "coldfront.plugins.qumulo.utils.acl_allocations."
                        "ActiveDirectoryAPI"
                    )
                ) as mock_ad_api:
                    self.assertTrue(view.form_valid(form))
                    mock_async_task.assert_called_once_with(
                        reset_allocation_acls,
                        self.user.email,
                        self.storage_allocation,
                        trueFalse,
                        hook=acl_reset_complete_hook,
                        q_options={
                            'retry': 90000,
                            'timeout': 86400
                        }
                    )
