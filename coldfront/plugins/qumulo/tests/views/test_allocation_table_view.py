from django.test import TestCase, RequestFactory
from unittest.mock import patch, MagicMock

from coldfront.core.allocation.models import Allocation

from coldfront.plugins.qumulo.tests.utils.mock_data import (
    build_models,
    create_allocation,
    build_user_plus_project,
)
from coldfront.plugins.qumulo.views.allocation_table_view import (
    AllocationTableView,
)


class AllocationTableViewTests(TestCase):
    def setUp(self):
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
            "department_number": "Time Travel Services",
            "service_rate": "general",
        }

        self.allocation = create_allocation(self.project, self.user, self.form_data)

    def test_get_queryset(self):
        request = RequestFactory().get(
            "src/coldfront.plugins.qumulo/views/allocation_table_view.py"
        )
        view = AllocationTableView()
        view.request = request

        qs = view.get_queryset()

        self.assertEqual(len(qs), 1)
        self.assertEqual(qs[0].id, self.allocation.id)

    def test_search_and_filtering(self):

        # call build_models again to get a different set of projects/users
        other_models = build_user_plus_project(
            username="jack.frost", project_name="Ice Age Project"
        )

        other_project = other_models["project"]
        other_user = other_models["user"]

        other_form_data = {
            "storage_filesystem_path": "xyz",
            "storage_export_path": "abc",
            "storage_ticket": "ITSD-78910",
            "storage_name": "general_store",
            "storage_quota": 8,
            "protocols": ["nfs"],
            "rw_users": ["test2"],
            "ro_users": ["test3"],
            "cost_center": "Scrooge McDuck",
            "department_number": "Whale-watching",
            "service_rate": "consumption",
        }

        other_allocation = create_allocation(other_project, other_user, other_form_data)

        query_params = {"department_number": "Whale-watching"}
        request = RequestFactory().get(
            "src/coldfront.plugins.qumulo/views/allocation_table_view.py",
            data=query_params,
        )
        view = AllocationTableView()
        view.request = request

        qs = view.get_queryset()

        self.assertEqual(len(qs), 1)
        self.assertEqual(qs[0].id, other_allocation.id)

    def test_result_pagination(self):
        # call build_models again to get a different set of projects/users
        other_models = build_user_plus_project(
            username="jack.frost", project_name="Ice Age Project"
        )
        # create project
        other_project = other_models["project"]
        other_user = other_models["user"]

        other_form_data = {
            "storage_filesystem_path": "xyz",
            "storage_export_path": "abc",
            "storage_ticket": "ITSD-78910",
            "storage_name": "general_store",
            "storage_quota": 8,
            "protocols": ["nfs"],
            "rw_users": ["test2"],
            "ro_users": ["test3"],
            "cost_center": "Scrooge McDuck",
            "department_number": "Whale-watching",
            "service_rate": "consumption",
        }

        other_allocations = []

        # create 4 more allocations to test that will match
        # the query
        for i in range(4):
            other_allocations.append(
                create_allocation(other_project, other_user, other_form_data)
            )

        query_params = {"department_number": "Whale-watching"}
        request = RequestFactory().get(
            "src/coldfront.plugins.qumulo/views/allocation_table_view.py",
            data=query_params,
        )
        view = AllocationTableView()
        view.request = request

        qs = view.get_queryset()

        self.assertEqual(len(qs), 4)

        result_ids = [x.id for x in qs]
        underlying_ids = [x.id for x in other_allocations]
        self.assertEqual(result_ids, underlying_ids)

        # test pagination
        first_page_by_two = view._handle_pagination(qs, 1, 2)
        second_page_by_two = view._handle_pagination(qs, 2, 2)
        third_page_by_two = view._handle_pagination(qs, 3, 2)

        first_page_by_three = view._handle_pagination(qs, 1, 3)
        second_page_by_three = view._handle_pagination(qs, 2, 3)
        third_page_by_three = view._handle_pagination(qs, 3, 3)

        # by default, the returned results should be ordered by ID

        first_page_by_two_ids = [alloc.id for alloc in first_page_by_two.object_list]
        second_page_by_two_ids = [alloc.id for alloc in second_page_by_two.object_list]

        first_page_by_three_ids = [
            alloc.id for alloc in first_page_by_three.object_list
        ]
        second_page_by_three_ids = [
            alloc.id for alloc in second_page_by_three.object_list
        ]

        expected_first_page_by_two_ids = [alloc.id for alloc in other_allocations[:2]]
        expected_second_page_by_two_ids = [alloc.id for alloc in other_allocations[2:4]]

        expected_first_page_by_three_ids = [alloc.id for alloc in other_allocations[:3]]
        expected_second_page_by_three_ids = [
            alloc.id for alloc in other_allocations[3:6]
        ]

        self.assertEqual(first_page_by_two_ids, expected_first_page_by_two_ids)
        self.assertEqual(second_page_by_two_ids, expected_second_page_by_two_ids)

        self.assertEqual(first_page_by_three_ids, expected_first_page_by_three_ids)
        self.assertEqual(second_page_by_three_ids, expected_second_page_by_three_ids)

        # NOTE: if you "go past the end", you get the last valid page
        # instead
        self.assertEqual(third_page_by_two.object_list, second_page_by_two.object_list)
        self.assertEqual(
            third_page_by_three.object_list, second_page_by_three.object_list
        )
