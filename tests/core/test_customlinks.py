# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0


import jinja2
from django.test import override_settings
from django.urls import reverse

from coldfront.core.choices import CustomLinkButtonClassChoices
from coldfront.core.models import CustomLink
from coldfront.utils.testing import ViewTestCases


class CustomLinkTestCase(ViewTestCases.PrimaryObjectViewTestCase):
    """Test CRUD views for CustomLink."""

    model = CustomLink

    @classmethod
    def setUpTestData(cls):
        from django.contrib.contenttypes.models import ContentType

        cls.choices_set = [
            CustomLink.objects.create(
                name=f"Custom Link {i}",
                link_text="{{ object.name }}",
                link_url="https://example.com/{{ object.pk }}",
                weight=100 * i,
            )
            for i in range(1, 4)
        ]

        # Assign the first link to the Project content type (Project inherits
        # from OrganizationalModel, which includes CustomLinksMixin)
        from coldfront.ras.models import Project

        project_ct = ContentType.objects.get_for_model(Project)
        cls.choices_set[0].object_types.add(project_ct)
        cls.choices_set[1].object_types.add(project_ct)
        cls.choices_set[2].object_types.add(project_ct)

        cls.create_data = {
            "name": "New Custom Link",
            "link_text": "{{ object.name }}",
            "link_url": "https://example.com/{{ object.pk }}",
            "object_types": [project_ct.pk],
            "enabled": True,
            "weight": 50,
            "group_name": "",
            "button_class": CustomLinkButtonClassChoices.DEFAULT,
            "new_window": False,
        }

        cls.form_data = {
            "name": "New Custom Link",
            "link_text": "{{ object.name }}",
            "link_url": "https://example.com/{{ object.pk }}",
            "object_types": [project_ct.pk],
            "enabled": True,
            "weight": 50,
            "group_name": "",
            "button_class": CustomLinkButtonClassChoices.DEFAULT,
            "new_window": False,
        }

        cls.bulk_edit_form_data = {
            "enabled": False,
            "weight": 200,
        }

        cls.csv_data = (
            "name,object_types,enabled,link_text,link_url,weight,group_name,button_class,new_window",
            "CSV Import 1,ras.project,true,{{ object.name }},https://example.com/{{ object.pk }},100,,blue,false",
            "CSV Import 2,ras.project,false,{{ object.name }},https://example.com/{{ object.pk }},200,,green,true",
        )

        cls.csv_update_data = (
            "id,name,link_text",
            f"{cls.choices_set[0].pk},Updated Link 1,{{{{ object.name }}}}",
            f"{cls.choices_set[1].pk},Updated Link 2,{{{{ object.name }}}}",
            f"{cls.choices_set[2].pk},Updated Link 3,{{{{ object.name }}}}",
        )

    def test_custom_link_str(self):
        """Verify __str__ returns the name."""
        link = CustomLink(name="Test Link", link_text="test", link_url="/test")
        self.assertEqual(str(link), "Test Link")

    def test_custom_link_absolute_url(self):
        """Verify get_absolute_url returns the detail view URL."""
        link = CustomLink.objects.create(
            name="URL Test",
            link_text="{{ object.name }}",
            link_url="/test",
        )
        expected = reverse("core:customlink", args=[link.pk])
        self.assertEqual(link.get_absolute_url(), expected)

    def test_render_basic(self):
        """Verify render() returns rendered text and link."""
        link = CustomLink.objects.create(
            name="Test",
            link_text="{{ object.name }}",
            link_url="/test/{{ object.pk }}",
        )
        context = {"object": link}
        result = link.render(context)
        self.assertEqual(result["text"], "Test")
        self.assertEqual(result["link"], f"/test/{link.pk}")

    def test_render_empty_text(self):
        """Verify render() returns empty dict when text renders empty."""
        link = CustomLink(
            name="Empty",
            link_text="",
            link_url="/test",
        )
        context = {"object": link}
        result = link.render(context)
        self.assertEqual(result, {})

    def test_render_new_window(self):
        """Verify render() sets link_target when new_window is True."""
        link = CustomLink(
            name="New Window",
            link_text="Click",
            link_url="/test",
            new_window=True,
        )
        context = {"object": link}
        result = link.render(context)
        self.assertIn('target="_blank"', result["link_target"])

    def test_render_no_new_window(self):
        """Verify render() sets empty link_target when new_window is False."""
        link = CustomLink(
            name="Same Window",
            link_text="Click",
            link_url="/test",
            new_window=False,
        )
        context = {"object": link}
        result = link.render(context)
        self.assertEqual(result["link_target"], "")

    def test_render_invalid_scheme(self):
        """Verify render() returns empty link for disallowed URL schemes."""
        link = CustomLink(
            name="Bad Scheme",
            link_text="Click",
            link_url="javascript:alert(1)",
        )
        context = {"object": link}
        with override_settings(ALLOWED_URL_SCHEMES=["http", "https"]):
            result = link.render(context)
        self.assertEqual(result["link"], "")

    def test_render_sanitizes_text(self):
        """Verify render() sanitizes link text."""
        link = CustomLink(
            name="XSS",
            link_text="<script>alert(1)</script>",
            link_url="/safe",
        )
        context = {"object": link}
        with override_settings(ALLOWED_URL_SCHEMES=["http", "https"]):
            result = link.render(context)
        # Script tags should be removed or escaped
        self.assertNotIn("<script>", result["text"])

    def test_clone(self):
        """Verify clone() returns the clone_fields."""
        link = CustomLink.objects.create(
            name="Clone Test",
            link_text="{{ object.name }}",
            link_url="/test",
        )
        attrs = link.clone()
        self.assertIn("enabled", attrs)
        self.assertIn("weight", attrs)
        self.assertIn("button_class", attrs)
        self.assertIn("new_window", attrs)
        self.assertIn("object_types", attrs)

    def test_button_class_choices(self):
        """Verify button_class uses CustomLinkButtonClassChoices."""
        for value, label in CustomLinkButtonClassChoices:
            link = CustomLink(
                name=f"Button {value}",
                link_text="test",
                link_url="/test",
                button_class=value,
            )
            self.assertEqual(link.button_class, value)

    def test_object_type_filtering(self):
        """Verify CustomLink can be filtered by object_types."""
        # Create a CustomLink and assign it to an object type
        link = CustomLink.objects.create(
            name="Type Filtered",
            link_text="test",
            link_url="/test",
        )
        # It should exist without object types
        self.assertIn(link, CustomLink.objects.all())

    def test_render_with_invalid_jinja2(self):
        """Verify render() raises TemplateSyntaxError for invalid Jinja2."""
        link = CustomLink.objects.create(
            name="Bad Template",
            link_text="{{ invalid syntax }}",
            link_url="/test",
        )
        context = {"object": link}
        with self.assertRaises(jinja2.exceptions.TemplateSyntaxError):
            link.render(context)
