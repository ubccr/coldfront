from django.test import TestCase, tag
from django.http import HttpRequest

from coldfront.plugins.qumulo.api.active_directory_members import ActiveDirectoryMembers

import json


class TestActiveDirectoryMembersGet(TestCase):
    @tag("integration")
    def test_returns_empty_list(self):
        active_directory_api = ActiveDirectoryMembers()

        request = HttpRequest()
        request.method = "GET"

        response = active_directory_api.get(request)
        content = json.loads(response.content)

        self.assertEqual(content["validNames"], [])

    @tag("integration")
    def test_returns_valid_names(self):
        members = ["harterj"]
        active_directory_api = ActiveDirectoryMembers()

        request = HttpRequest()
        request.method = "GET"

        for member in members:
            request.GET.update({"members[]": member})

        response = active_directory_api.get(request)
        content = json.loads(response.content)

        self.assertListEqual(content["validNames"], members)

    @tag("integration")
    def test_returns_valid_names_and_not_invalid_names(self):
        good_members = ["harterj"]
        bad_members = ["invalid_member"]
        members = good_members + bad_members
        active_directory_api = ActiveDirectoryMembers()

        request = HttpRequest()
        request.method = "GET"

        for member in members:
            request.GET.update({"members[]": member})

        response = active_directory_api.get(request)
        content = json.loads(response.content)

        self.assertListEqual(content["validNames"], good_members)

    @tag("integration")
    def test_returns_empty_list_with_only_invalid_names(self):
        members = ["invalid_member"]
        active_directory_api = ActiveDirectoryMembers()

        request = HttpRequest()
        request.method = "GET"

        for member in members:
            request.GET.update({"members[]": member})

        response = active_directory_api.get(request)
        content = json.loads(response.content)

        self.assertListEqual(content["validNames"], [])
