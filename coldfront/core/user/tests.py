from selenium.webdriver.common.keys import Keys
from coldfront.core.test_helpers.factories import UserFactory
from django.test import TestCase

from coldfront.core.test_helpers.factories import (
    UserFactory,
)

from django.test import TestCase

from django.test import LiveServerTestCase
from selenium import webdriver
from selenium.webdriver.support.ui import Select

from coldfront.core.user.models import UserProfile
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

    def test_pi(self):

    #tests pi login
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
        print("\nLogged in successfully.")

    #tests adding project for pi
        if(driver.find_element_by_id("hamburger_icon").is_displayed()):
            driver.find_element_by_id("hamburger_icon").click()
        
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
        print("\nProject created successfully.")

    #tests adding allocation request for pi
        request_button = driver.find_element_by_id("resource_button")
        request_button.click()

        justification_box = driver.find_element_by_id("id_justification")
        justification_box.send_keys("This is a test justification.")
        submit_button = driver.find_element_by_id("submit_req")
        submit_button.click()
        print("\nAllocation request submitted successfully.")

        assert driver.current_url.__contains__("project")

    #tests adding/removing publication

        add_publication = driver.find_element_by_id("add_publication")
        add_publication.click()

        manually_add = driver.find_element_by_id("manual_add")
        manually_add.click()

        title = driver.find_element_by_id("id_title")
        title.send_keys("Test Title")
        author = driver.find_element_by_id("id_author")
        author.send_keys("Test Author")
        year = driver.find_element_by_id("id_year")
        year.send_keys("2000")
        journal = driver.find_element_by_id("id_journal")
        journal.send_keys("Test Journal")
        submit_publ = driver.find_element_by_id("submit_manually")
        submit_publ.click()

        # box = driver.find_element_by_id("id_search_id")
        # box.send_keys("10.1038/nphys1170")
        # search_button = driver.find_element_by_id("search-button")
        # search_button.click()
        # checkbox_for_publication = driver.find_element_by_id("selectAll")
        # checkbox_for_publication.click()
        # add_button = driver.find_element_by_id("add_publ")
        # add_button.click()
        print("\nPublication added successfully.")


        del_button = driver.find_element_by_id("delete_publ")
        del_button.click()
        all_publications = driver.find_element_by_id("selectAll")
        all_publications.click()
        submit_delete = driver.find_element_by_id("delete")
        submit_delete.click()
        print("\nPublication deleted successfully.")
        
        assert driver.current_url.__contains__("project")

    #tests adding/removing grant

        # add_grant = driver.find_element_by_id("add_grant")
        # add_grant.click()

        # title = driver.find_element_by_id("id_title")
        # title.send_keys("Test Title")
        # grant_number = driver.find_element_by_id("id_grant_number")
        # grant_number.send_keys("123")
        # role = Select(driver.find_element_by_id("id_role"))
        # role.select_by_value("PI")
        # agency = Select(driver.find_element_by_id("id_funding_agency"))
        # agency.select_by_value("11")
        # start_date = driver.find_element_by_id("id_grant_start")
        # start_date.send_keys("2022-11-01")
        # end_date = driver.find_element_by_id("id_grant_end")
        # end_date.send_keys("2025-11-01")
        # credit = driver.find_element_by_id("id_percent_credit")
        # credit.send_keys("10")
        # funding = driver.find_element_by_id("id_direct_funding")
        # funding.send_keys("1000")
        # award = driver.find_element_by_id("id_total_amount_awarded")
        # award.send_keys("10000")
        # status = Select(driver.find_element_by_id("id_status"))
        # status.select_by_value("1")
        # submit_grant = driver.find_element_by_id("grant_save")
        # submit_grant.click()
        # print("\nGrant added successfully.")

        # del_button = driver.find_element_by_id("delete_grant")
        # del_button.click()
        # all_grants = driver.find_element_by_id("selectAll")
        # all_grants.click()
        # submit_delete_g = driver.find_element_by_id("delete_grants")
        # submit_delete_g.click()
        # print("\nGrant deleted successfully.")
        
        # assert driver.current_url.__contains__("project")

    #tests reviewing project for pi
        driver.get('http://127.0.0.1:8000/project/1/review')
        if(driver.title.__contains__("Review")):
            reason = driver.find_element_by_id("id_reason")
            reason.send_keys("N/A")
            acknowledgement = driver.find_element_by_id("id_acknowledgement")
            acknowledgement.click()
            submit = driver.find_element_by_id("submit_review")
            submit.click()
            print("\nProject reviewed successfully.")

    #tests requesting allocation change for pi
        if(driver.find_element_by_id("hamburger_icon").is_displayed()):
            driver.find_element_by_id("hamburger_icon").click()
        
        driver.find_element_by_id("project_dropdown").click()
        driver.find_element_by_id("navbar-allocation").click()

        driver.get('http://127.0.0.1:8000/allocation/1')

        change_button = driver.find_element_by_id("request_change")
        change_button.click()

        extension = Select(driver.find_element_by_id("id_end_date_extension"))
        extension.select_by_value("30")
        change_justification = driver.find_element_by_id("id_justification")
        change_justification.send_keys("This is a test justification.")
        submit_change = driver.find_element_by_id("submit_change")
        submit_change.click()
        print("\nAllocation change submitted successfully.")

        assert driver.current_url.__contains__("allocation")
