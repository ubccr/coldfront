from django.test import TestCase
from django.http import HttpRequest, QueryDict

from unittest.mock import patch

from coldfront.plugins.qumulo.api.allocations import Allocations
from coldfront.plugins.qumulo.services.allocation_service import AllocationService
from coldfront.core.allocation.models import AllocationStatusChoice, Allocation, Project

from coldfront.plugins.qumulo.tests.utils.mock_data import (
    build_models,
    default_form_data,
)

import json


@patch("coldfront.plugins.qumulo.services.allocation_service.async_task")
@patch("coldfront.plugins.qumulo.services.allocation_service.ActiveDirectoryAPI")
class TestAllocationsGet(TestCase):
    def setUp(self) -> None:
        build_data = build_models()

        self.user = build_data["user"]
        self.project: Project = build_data["project"]

        return super().setUp()

    def test_returns_empty_list(self, _, __) -> None:
        allocations = Allocations()

        request = HttpRequest()
        request.method = "GET"
        response = allocations.get(request)
        content = json.loads(response.content)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(content["totalPages"], 0)
        self.assertEqual(content["allocations"], [])

    def test_returns_all_allocations(self, _, __) -> None:
        num_allocations = 3
        for i in range(num_allocations):
            form_data = default_form_data.copy()
            form_data["project_pk"] = self.project.pk
            form_data["storage_filesystem_path"] = f"test_path_{i}"

            AllocationService.create_new_allocation(form_data, self.user)

        allocations = Allocations()

        request = HttpRequest()
        request.method = "GET"
        response = allocations.get(request)
        content = json.loads(response.content)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(content["totalPages"], 1)
        self.assertEqual(len(content["allocations"]), num_allocations)

    def test_returns_allocations_with_correct_data(self, _, __) -> None:
        expected_keys = [
            "id",
            "project",
            "status",
            "quantity",
            "start_date",
            "end_date",
            "justification",
            "description",
            "is_locked",
            "is_changeable",
            "resources",
            "attributes",
        ]

        form_data = default_form_data.copy()
        form_data["project_pk"] = self.project.pk
        form_data["storage_filesystem_path"] = f"test_path"

        AllocationService.create_new_allocation(form_data, self.user)

        allocations = Allocations()

        request = HttpRequest()
        request.method = "GET"
        response = allocations.get(request)
        content = json.loads(response.content)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(content["allocations"]), 1)

        response_allocation = content["allocations"][0]
        self.assertEqual(set(response_allocation.keys()), set(expected_keys))

    def test_returns_max_100_results(self, _, __) -> None:
        num_allocations = 105
        for i in range(num_allocations):
            form_data = default_form_data.copy()
            form_data["project_pk"] = self.project.pk
            form_data["storage_filesystem_path"] = f"test_path_{i}"

            AllocationService.create_new_allocation(form_data, self.user)

        allocations = Allocations()

        request = HttpRequest()
        request.method = "GET"
        response = allocations.get(request)
        content = json.loads(response.content)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(content["allocations"]), 100)
        self.assertEqual(content["totalPages"], 2)

    def test_returns_next_100_results(self, _, __) -> None:
        num_allocations = 105
        for i in range(num_allocations):
            form_data = default_form_data.copy()
            form_data["project_pk"] = self.project.pk
            form_data["storage_filesystem_path"] = f"test_path_{i}"

            AllocationService.create_new_allocation(form_data, self.user)

        allocations = Allocations()

        request = HttpRequest()
        request.method = "GET"
        request.GET.update({"page": 2})
        response = allocations.get(request)
        content = json.loads(response.content)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(content["allocations"]), 5)

    def test_allows_specific_result_count(self, _, __) -> None:
        num_allocations = 30
        for i in range(num_allocations):
            form_data = default_form_data.copy()
            form_data["project_pk"] = self.project.pk
            form_data["storage_filesystem_path"] = f"test_path_{i}"

            AllocationService.create_new_allocation(form_data, self.user)

        allocations = Allocations()

        request = HttpRequest()
        request.method = "GET"
        request.GET.update({"page": 1, "limit": 20})
        response = allocations.get(request)
        content = json.loads(response.content)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(content["allocations"]), 20)

        request.GET.update({"page": 2, "limit": 20})
        response = allocations.get(request)
        content = json.loads(response.content)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(content["allocations"]), 10)

    def test_sorts_by_basic_keys(self, _, __) -> None:
        num_allocations = 3
        id_map = []
        for i in range(num_allocations):
            form_data = default_form_data.copy()
            form_data["project_pk"] = self.project.pk
            form_data["storage_filesystem_path"] = f"test_path_{i}"

            allocation_data = AllocationService.create_new_allocation(
                form_data, self.user
            )
            allocation: Allocation = allocation_data.get("allocation")

            id_map.append(allocation.id)

            if i == 1:
                active_status = AllocationStatusChoice.objects.get_or_create(
                    name="TestStatus"
                )[0]
                allocation.status = active_status
                allocation.save()

        allocations = Allocations()

        request = HttpRequest()
        request.method = "GET"
        request.GET.update({"sort": "id"})
        response = allocations.get(request)
        content = json.loads(response.content)

        self.assertEqual(response.status_code, 200)
        response_data = content["allocations"]
        self.assertLessEqual(response_data[0]["id"], response_data[1]["id"])
        self.assertLessEqual(response_data[1]["id"], response_data[2]["id"])

        request.GET.update({"sort": "-id"})
        response = allocations.get(request)
        content = json.loads(response.content)

        self.assertEqual(response.status_code, 200)
        response_data = content["allocations"]
        self.assertGreaterEqual(response_data[0]["id"], response_data[1]["id"])
        self.assertGreaterEqual(response_data[1]["id"], response_data[2]["id"])

        request.GET.update({"sort": "status"})
        response = allocations.get(request)
        content = json.loads(response.content)

        self.assertEqual(response.status_code, 200)
        response_data = content["allocations"]
        self.assertEqual(response_data[2]["id"], id_map[1])

        request.GET.update({"sort": "-status"})
        response = allocations.get(request)
        content = json.loads(response.content)

        self.assertEqual(response.status_code, 200)
        response_data = content["allocations"]
        self.assertEqual(response_data[0]["id"], id_map[1])

    def test_throws_error_on_invalid_sort_key(self, _, __) -> None:
        allocations = Allocations()

        request = HttpRequest()
        request.method = "GET"
        request.GET.update({"sort": "storage_filesystem_path"})
        response = allocations.get(request)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.content.decode(), "Invalid sort key")

    def test_sorts_by_attribute(self, _, __) -> None:
        num_allocations = 3
        for i in range(num_allocations):
            form_data = default_form_data.copy()
            form_data["project_pk"] = self.project.pk
            form_data["storage_filesystem_path"] = f"test_path_{i}"

            if i == 1:
                form_data["storage_filesystem_path"] = "zzz"
            AllocationService.create_new_allocation(form_data, self.user)

        allocations = Allocations()

        request = HttpRequest()
        request.method = "GET"
        request.GET.update(
            {
                "sort": "attributes__storage_filesystem_path",
            }
        )
        response = allocations.get(request)
        content = json.loads(response.content)

        self.assertEqual(response.status_code, 200)
        response_data = content["allocations"]
        self.assertLessEqual(
            response_data[0]["attributes"]["storage_filesystem_path"],
            response_data[1]["attributes"]["storage_filesystem_path"],
        )
        self.assertLessEqual(
            response_data[1]["attributes"]["storage_filesystem_path"],
            response_data[2]["attributes"]["storage_filesystem_path"],
        )

        request.GET.update(
            {
                "sort": "-attributes__storage_filesystem_path",
            }
        )
        response = allocations.get(request)
        content = json.loads(response.content)

        self.assertEqual(response.status_code, 200)
        response_data = content["allocations"]
        self.assertLessEqual(
            response_data[2]["attributes"]["storage_filesystem_path"],
            response_data[1]["attributes"]["storage_filesystem_path"],
        )
        self.assertLessEqual(
            response_data[1]["attributes"]["storage_filesystem_path"],
            response_data[0]["attributes"]["storage_filesystem_path"],
        )

    def test_filters_on_basic_keys(self, _, __) -> None:
        num_allocations = 3
        id_map = []
        for i in range(num_allocations):
            form_data = default_form_data.copy()
            form_data["project_pk"] = self.project.pk
            form_data["storage_filesystem_path"] = f"test_path_{i}"

            allocation_data = AllocationService.create_new_allocation(
                form_data, self.user
            )
            allocation: Allocation = allocation_data.get("allocation")

            id_map.append(allocation.id)

            if i == 1:
                active_status = AllocationStatusChoice.objects.get_or_create(
                    name="TestStatus"
                )[0]
                allocation.status = active_status
                allocation.save()

        allocations = Allocations()

        request = HttpRequest()
        request.method = "GET"
        request.GET.setlist("search[]", ["id:1"])
        response = allocations.get(request)
        content = json.loads(response.content)

        self.assertEqual(response.status_code, 200)
        response_data = content["allocations"]
        self.assertEqual(len(response_data), 1)
        self.assertEqual(response_data[0]["id"], 1)

        request.GET.setlist("search[]", ["status__name:TestStatus"])
        response = allocations.get(request)
        content = json.loads(response.content)

        self.assertEqual(response.status_code, 200)
        response_data = content["allocations"]
        self.assertEqual(len(response_data), 1)
        self.assertEqual(response_data[0]["id"], id_map[1])

    def test_filters_on_multiple_basic_keys(self, _, __) -> None:
        num_allocations = 3
        id_map = []
        for i in range(num_allocations):
            form_data = default_form_data.copy()
            form_data["project_pk"] = self.project.pk
            form_data["storage_filesystem_path"] = f"test_path_{i}"

            if i == 2:
                new_project = Project.objects.create(
                    title="TestProject2",
                    pi=self.user,
                    status=self.project.status,
                    field_of_science=self.project.field_of_science,
                )
                form_data["project_pk"] = new_project.pk

            allocation_data = AllocationService.create_new_allocation(
                form_data, self.user
            )
            allocation: Allocation = allocation_data.get("allocation")

            id_map.append(allocation.id)

            if i == 1:
                active_status = AllocationStatusChoice.objects.get_or_create(
                    name="TestStatus"
                )[0]
                allocation.status = active_status
                allocation.save()

        allocations = Allocations()

        request = HttpRequest()
        request.method = "GET"
        request.GET.setlist(
            "search[]", [f"project__pk:{self.project.pk}", "status__name:Pending"]
        )
        response = allocations.get(request)
        content = json.loads(response.content)

        self.assertEqual(response.status_code, 200)
        response_data = content["allocations"]
        self.assertEqual(len(response_data), 1)
        self.assertEqual(response_data[0]["id"], id_map[0])

    def test_filters_on_attributes(self, _, __) -> None:
        num_allocations = 3
        id_map = []
        for i in range(num_allocations):
            form_data = default_form_data.copy()
            form_data["project_pk"] = self.project.pk
            form_data["storage_filesystem_path"] = f"test_path_{i}"

            allocation_data = AllocationService.create_new_allocation(
                form_data, self.user
            )
            allocation: Allocation = allocation_data.get("allocation")

            id_map.append(allocation.id)

        allocations = Allocations()

        request = HttpRequest()
        request.method = "GET"
        request.GET.setlist(
            "search[]", ["attributes__storage_filesystem_path:test_path_1"]
        )
        response = allocations.get(request)
        content = json.loads(response.content)

        self.assertEqual(response.status_code, 200)
        response_data = content["allocations"]
        self.assertEqual(len(response_data), 1)
        self.assertEqual(response_data[0]["id"], id_map[1])

    def test_sorts_filtered_results(self, _, __) -> None:
        num_allocations = 3
        id_map = []
        for i in range(num_allocations):
            form_data = default_form_data.copy()
            form_data["project_pk"] = self.project.pk
            form_data["storage_filesystem_path"] = f"test_path_{i}"

            allocation_data = AllocationService.create_new_allocation(
                form_data, self.user
            )
            allocation: Allocation = allocation_data.get("allocation")

            id_map.append(allocation.id)

            if i == 1:
                active_status = AllocationStatusChoice.objects.get_or_create(
                    name="TestStatus"
                )[0]
                allocation.status = active_status
                allocation.save()

        allocations = Allocations()

        request = HttpRequest()
        request.method = "GET"
        request.GET.update({"sort": "id"})
        request.GET.setlist("search[]", ["status__name:Pending"])
        response = allocations.get(request)
        content = json.loads(response.content)

        self.assertEqual(response.status_code, 200)
        response_data = content["allocations"]
        self.assertEqual(len(response_data), 2)
        self.assertLessEqual(response_data[0]["id"], response_data[1]["id"])

        request.GET.update({"sort": "-id"})
        response = allocations.get(request)
        content = json.loads(response.content)

        self.assertEqual(response.status_code, 200)
        response_data = content["allocations"]
        self.assertEqual(len(response_data), 2)
        self.assertGreaterEqual(response_data[0]["id"], response_data[1]["id"])
