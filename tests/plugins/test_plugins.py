# SPDX-FileCopyrightText: (C) DigitalOcean, LLC
# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from unittest import skipIf

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from coldfront.core.models import ObjectType
from coldfront.plugins.navigation import PluginMenu, PluginMenuButton, PluginMenuItem
from coldfront.plugins.utils import get_plugin_config
from coldfront.registry import registry
from coldfront.utils.testing import APITestCase
from tests.dummy_plugin import config as dummy_config


@skipIf("tests.dummy_plugin" not in settings.PLUGINS, "dummy_plugin not in settings.PLUGINS")
class PluginTest(TestCase):
    def test_config(self):

        self.assertIn("tests.dummy_plugin.DummyPluginConfig", settings.INSTALLED_APPS)

    def test_model_registration(self):
        self.assertTrue(ObjectType.objects.filter(app_label="dummy_plugin", model="dummymodel").exists())

    def test_get_absolute_url_plugin(self):
        from tests.dummy_plugin.models import DummyColdFrontModel

        m = DummyColdFrontModel()
        m.pk = 123

        self.assertEqual(m.get_absolute_url(), f"/plugins/dummy-plugin/coldfrontmodel/{m.pk}/")

    def test_models(self):
        from tests.dummy_plugin.models import DummyModel

        # Test saving an instance
        instance = DummyModel(name="Instance 1", number=100)
        instance.save()
        self.assertIsNotNone(instance.pk)

        # Test deleting an instance
        instance.delete()
        self.assertIsNone(instance.pk)

    def test_registered_columns(self):
        """
        Check that a plugin can register a custom column on a core model table.
        """
        from coldfront.ras.models import Project
        from coldfront.ras.tables import ProjectTable

        table = ProjectTable(Project.objects.all())
        self.assertIn("foo", table.columns.names())

    @override_settings(LOGIN_REQUIRED=True)
    def test_views(self):

        # Test URL resolution
        url = reverse("plugins:dummy_plugin:dummy_model_list")
        self.assertEqual(url, "/plugins/dummy-plugin/models/")

        # Test GET request
        client = Client()
        response = client.get(url)
        self.assertEqual(response.status_code, 200)

    @override_settings(LOGIN_REQUIRED=False)
    def test_registered_views(self):

        # Test URL resolution
        url = reverse("ras:project_extra", kwargs={"pk": 1})
        self.assertEqual(url, "/ras/projects/1/other-stuff/")

        # Test GET request
        client = Client()
        response = client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_menu(self):
        """
        Check menu registration.
        """
        menu = registry["plugins"]["menus"][0]
        self.assertIsInstance(menu, PluginMenu)
        self.assertEqual(menu.label, "Dummy Plugin")

    def test_menu_items(self):
        """
        Check menu_items registration.
        """
        self.assertIn("Dummy plugin", registry["plugins"]["menu_items"])
        menu_items = registry["plugins"]["menu_items"]["Dummy plugin"]
        self.assertEqual(len(menu_items), 2)
        self.assertEqual(len(menu_items[0].buttons), 2)

    def test_template_extensions(self):
        """
        Check that plugin TemplateExtensions are registered.
        """
        from tests.dummy_plugin.template_content import GlobalContent, ProjectContent

        self.assertIn(GlobalContent, registry["plugins"]["template_extensions"][None])
        self.assertIn(ProjectContent, registry["plugins"]["template_extensions"]["ras.project"])

    def test_middleware(self):
        """
        Check that plugin middleware is registered.
        """
        self.assertIn("tests.dummy_plugin.middleware.DummyMiddleware", settings.MIDDLEWARE)

    def test_min_version(self):
        """
        Check enforcement of minimum ColdFront version.
        """
        with self.assertRaises(ImproperlyConfigured):
            dummy_config.validate({}, "0.9")

    def test_max_version(self):
        """
        Check enforcement of maximum ColdFront version.
        """
        with self.assertRaises(ImproperlyConfigured):
            dummy_config.validate({}, "10.0")

    def test_required_settings(self):
        """
        Validate enforcement of required settings.
        """

        class DummyConfigWithRequiredSettings(dummy_config):
            required_settings = ["foo"]

        # Validation should pass when all required settings are present
        DummyConfigWithRequiredSettings.validate({"foo": True}, settings.VERSION)

        # Validation should fail when a required setting is missing
        with self.assertRaises(ImproperlyConfigured):
            DummyConfigWithRequiredSettings.validate({}, settings.VERSION)

    def test_default_settings(self):
        """
        Validate population of default config settings.
        """

        class DummyConfigWithDefaultSettings(dummy_config):
            default_settings = {
                "bar": 123,
            }

        # Populate the default value if setting has not been specified
        user_config = {}
        DummyConfigWithDefaultSettings.validate(user_config, settings.VERSION)
        self.assertEqual(user_config["bar"], 123)

        # Don't overwrite specified values
        user_config = {"bar": 456}
        DummyConfigWithDefaultSettings.validate(user_config, settings.VERSION)
        self.assertEqual(user_config["bar"], 456)

    @override_settings(PLUGINS_CONFIG={"tests.dummy_plugin": {"foo": 123}})
    def test_get_plugin_config(self):
        """
        Validate that get_plugin_config() returns config parameters correctly.
        """
        plugin = "tests.dummy_plugin"
        self.assertEqual(get_plugin_config(plugin, "foo"), 123)
        self.assertEqual(get_plugin_config(plugin, "bar"), None)
        self.assertEqual(get_plugin_config(plugin, "bar", default=456), 456)


class PluginAPITest(APITestCase):
    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_api_views(self):

        # Test URL resolution
        url = reverse("plugins-api:dummy_plugin-api:dummymodel-list")
        self.assertEqual(url, "/api/plugins/dummy-plugin/dummy-models/")

        # Test GET request
        response = self.client.get(url, **self.header)
        self.assertEqual(response.status_code, 200)


class PluginNavigationTest(TestCase):
    def test_plugin_menu_item_independent_permissions(self):
        item1 = PluginMenuItem(link="test1", link_text="Test 1")
        item1.permissions.append("leaked_permission")

        item2 = PluginMenuItem(link="test2", link_text="Test 2")

        self.assertIsNot(item1.permissions, item2.permissions)
        self.assertEqual(item1.permissions, ["leaked_permission"])
        self.assertEqual(item2.permissions, [])

    def test_plugin_menu_item_independent_buttons(self):
        item1 = PluginMenuItem(link="test1", link_text="Test 1")
        button = PluginMenuButton(link="button1", title="Button 1", icon_class="mdi-test")
        item1.buttons.append(button)

        item2 = PluginMenuItem(link="test2", link_text="Test 2")

        self.assertIsNot(item1.buttons, item2.buttons)
        self.assertEqual(len(item1.buttons), 1)
        self.assertEqual(item1.buttons[0], button)
        self.assertEqual(item2.buttons, [])

    def test_plugin_menu_button_independent_permissions(self):
        button1 = PluginMenuButton(link="button1", title="Button 1", icon_class="mdi-test")
        button1.permissions.append("leaked_permission")

        button2 = PluginMenuButton(link="button2", title="Button 2", icon_class="mdi-test")

        self.assertIsNot(button1.permissions, button2.permissions)
        self.assertEqual(button1.permissions, ["leaked_permission"])
        self.assertEqual(button2.permissions, [])

    def test_explicit_permissions_remain_independent(self):
        item1 = PluginMenuItem(link="test1", link_text="Test 1", permissions=["explicit_permission"])
        item2 = PluginMenuItem(link="test2", link_text="Test 2", permissions=["different_permission"])

        self.assertIsNot(item1.permissions, item2.permissions)
        self.assertEqual(item1.permissions, ["explicit_permission"])
        self.assertEqual(item2.permissions, ["different_permission"])
