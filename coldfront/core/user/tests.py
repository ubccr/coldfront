from selenium.webdriver.common.keys import Keys
from coldfront.core.test_helpers.factories import UserFactory
from django.test import TestCase

from coldfront.core.test_helpers.factories import (
    UserFactory,
)

from django.test import TestCase

from django.test import LiveServerTestCase
from selenium import webdriver

from coldfront.core.user.models import UserProfile
import time

class TestUserProfile(TestCase):
    class Data:
        """Collection of test data, separated for readability"""

        def __init__(self):
            user = UserFactory(username='submitter')

            self.initial_fields = {
                'user': user,
                'is_pi': True,
                'id': user.id
            }
            
            self.unsaved_object = UserProfile(**self.initial_fields)
    
    def setUp(self):
        self.data = self.Data()

    def test_fields_generic(self):
        profile_obj = self.data.unsaved_object
        profile_obj.save()

        self.assertEqual(1, len(UserProfile.objects.all()))

        retrieved_profile = UserProfile.objects.get(pk=profile_obj.pk)

        for item in self.data.initial_fields.items():
            (field, initial_value) = item
            with self.subTest(item=item):
                saved_value = getattr(retrieved_profile, field)
                self.assertEqual(initial_value, saved_value)
        self.assertEqual(profile_obj, retrieved_profile)

    def test_user_on_delete(self):
        profile_obj = self.data.unsaved_object
        profile_obj.save()

        self.assertEqual(1, len(UserProfile.objects.all()))

        profile_obj.user.delete()

        # expecting CASCADE
        with self.assertRaises(UserProfile.DoesNotExist):
            UserProfile.objects.get(pk=profile_obj.pk)
        self.assertEqual(0, len(UserProfile.objects.all()))

class LoginTest(LiveServerTestCase):

    global driver
    driver = webdriver.Chrome()
    driver.get('http://127.0.0.1:8000/')


    #tests simple login for pi
    def testlogin(self):

        assert 'Welcome to' in driver.title
        driver.find_element_by_id("login_button").click()

        username = driver.find_element_by_id("id_username")
        password = driver.find_element_by_id("id_password")

        username.send_keys("a")
        password.send_keys("a")
        driver.find_element_by_id("login").click()

        username = driver.find_element_by_id("id_username")
        password = driver.find_element_by_id("id_password")
        username.send_keys(Keys.CONTROL + "a")
        username.send_keys(Keys.DELETE)
        username.send_keys("cgray")
        password.send_keys("test1234")
        driver.find_element_by_id("login").click()
        assert driver.current_url == 'http://127.0.0.1:8000/'

    #tests adding project for pi
        if(driver.find_element_by_id("hamburger_icon").is_displayed()):
            driver.find_element_by_id("hamburger_icon").click()
        else:
            driver.find_element_by_id("project_dropdown").click()
            driver.find_element_by_id("navbar-project").click()
            driver.find_element_by_id("add_project").click()

        title = driver.find_element_by_id("id_title")
        description = driver.find_element_by_id("id_description")

        title.send_keys("Test Title")
        description.clear()
        description = driver.find_element_by_id("id_description")
        description.send_keys("This is a test description > 10 characters.")
        driver.find_element_by_id("save_button").click()