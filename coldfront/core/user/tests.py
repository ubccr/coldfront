import pytest
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


# class PITests(LiveServerTestCase):

    # global driver
    # driver = webdriver.Chrome()
    # driver.get('http://127.0.0.1:8000/')

    # def test_pi(self):
    #     print("\nTesting PI controls:\n--------------------")

    #     # tests pi login
    #     assert 'Welcome to' in driver.title
    #     driver.find_element_by_id("login_button").click()

    #     username = driver.find_element_by_id("id_username")
    #     password = driver.find_element_by_id("id_password")

    #     username.send_keys("a")
    #     password.send_keys("a")
    #     driver.find_element_by_id("login").click()

    #     username = driver.find_element_by_id("id_username")
    #     password = driver.find_element_by_id("id_password")
    #     username.send_keys(Keys.CONTROL + "a")
    #     username.send_keys(Keys.DELETE)
    #     username.send_keys("cgray")
    #     password.send_keys("test1234")
    #     driver.find_element_by_id("login").click()
    #     assert driver.current_url == 'http://127.0.0.1:8000/'
    #     print("\nLogged in successfully.")

    #     # tests adding project for pi
    #     if (driver.find_element_by_id("hamburger_icon").is_displayed()):
    #         driver.find_element_by_id("hamburger_icon").click()

    #     driver.find_element_by_id("project_dropdown").click()
    #     driver.find_element_by_id("navbar-project").click()

    #     driver.find_element_by_id("add_project").click()

    #     title = driver.find_element_by_id("id_title")
    #     description = driver.find_element_by_id("id_description")

    #     title.send_keys("Test Title")
    #     description.clear()
    #     description = driver.find_element_by_id("id_description")
    #     description.send_keys("This is a test description > 10 characters.")
    #     driver.find_element_by_id("save_button").click()
    #     print("\nProject created successfully.")

    #     # tests adding allocation request for pi
    #     request_button = driver.find_element_by_id("resource_button")
    #     request_button.click()

    #     justification_box = driver.find_element_by_id("id_justification")
    #     justification_box.send_keys("This is a test justification.")
    #     submit_button = driver.find_element_by_id("submit_req")
    #     submit_button.click()
    #     print("\nAllocation request submitted successfully.")

    #     assert driver.current_url.__contains__("project")

    #     # tests adding/removing user from allocation -- need to add case when there are users to remove
    #     allocation_open = driver.find_element_by_id("allocation_open")
    #     allocation_open.click()

    #     add_user = driver.find_element_by_id("add_users_to_alloc")
    #     add_user.click()

    #     go_back = driver.find_element_by_id("back")
    #     go_back.click()
    #     print("\nNo users to add to allocation, but tested successfully.")

    #     remove_user = driver.find_element_by_id("remove_users_from_alloc")
    #     remove_user.click()

    #     go_back_again = driver.find_element_by_id("done_removing")
    #     go_back_again.click()
    #     print("\nNo users to remove from allocation, but tested successfully.")

    #     project_page = driver.find_element_by_id("project_name")
    #     project_page.click()

    #     # tests adding/removing user to/from project -- checkboxes not working

    #     # add_button = driver.find_element_by_id("user_add")
    #     # add_button.click()
    #     # search_box = driver.find_element_by_id("id_q")
    #     # search_box.send_keys("arivera")
    #     # actually_submit_search = driver.find_element_by_id("search-button")
    #     # actually_submit_search.click()
    #     # all_users = driver.find_element_by_id("id_allocationform-allocation_0")
    #     # all_users.click()
    #     # print(all_users)
    #     # add_add = driver.find_element_by_id("submit_user_add")
    #     # add_add.click()
    #     # print("\nUser added to project successfully.")

    #     # remove_button = driver.find_element_by_id("user_remove")
    #     # remove_button.click()
    #     # print("\nUser removed from project successfully.")

    #     # tests adding/removing publication -- checkboxes not working

    #     # box = driver.find_element_by_id("id_search_id")
    #     # box.send_keys("10.1038/nphys1170")
    #     # search_button = driver.find_element_by_id("search-button")
    #     # search_button.click()
    #     # checkbox_for_publication = driver.find_element_by_xpath("//input[@type='checkbox']")
    #     # checkbox_for_publication.click()
    #     # add_button = driver.find_element_by_id("add_publ")
    #     # add_button.click()
    #     # print("\nPublication added successfully.")

    #     add_publication = driver.find_element_by_id("add_publication")
    #     add_publication.click()

    #     manually_add = driver.find_element_by_id("manual_add")
    #     manually_add.click()

    #     title = driver.find_element_by_id("id_title")
    #     title.send_keys("Test Title")
    #     author = driver.find_element_by_id("id_author")
    #     author.send_keys("Test Author")
    #     year = driver.find_element_by_id("id_year")
    #     year.send_keys("2000")
    #     journal = driver.find_element_by_id("id_journal")
    #     journal.send_keys("Test Journal")
    #     submit_publ = driver.find_element_by_id("submit_manually")
    #     submit_publ.click()
    #     print("\nPublication added successfully.")

    #     del_button = driver.find_element_by_id("delete_publ")
    #     del_button.click()
    #     all_publications = driver.find_element_by_id("selectAll")
    #     all_publications.click()
    #     submit_delete = driver.find_element_by_id("delete")
    #     submit_delete.click()
    #     print("\nPublication deleted successfully.")

    #     assert driver.current_url.__contains__("project")

    #     # tests adding/removing output

    #     add_output = driver.find_element_by_id("add_output")
    #     add_output.click()

    #     title_output = driver.find_element_by_id("id_title")
    #     title_output.send_keys("Test Title")
    #     desc = driver.find_element_by_id("id_description")
    #     desc.send_keys("This is a test description.")
    #     save_output = driver.find_element_by_id("save_output")
    #     save_output.click()
    #     print("\nResearch output added successfully.")

    #     delete_output = driver.find_element_by_id("delete_output")
    #     delete_output.click()
    #     all_outputs = driver.find_elements_by_id("outputs")
    #     for element in all_outputs:
    #         element.click()
    #     actually_delete = driver.find_element_by_id("delete_outputs")
    #     actually_delete.click()
    #     print("\nResearch output deleted successfully.")

    #     assert driver.current_url.__contains__("project")

    #     # tests adding/removing grant -- datepicking is not working

    #     # add_grant = driver.find_element_by_id("add_grant")
    #     # add_grant.click()

    #     # title = driver.find_element_by_id("id_title")
    #     # title.send_keys("Test Title")
    #     # grant_number = driver.find_element_by_id("id_grant_number")
    #     # grant_number.send_keys("123")
    #     # role = Select(driver.find_element_by_id("id_role"))
    #     # role.select_by_value("PI")
    #     # agency = Select(driver.find_element_by_id("id_funding_agency"))
    #     # agency.select_by_value("11")
    #     # start_date = driver.find_element_by_id("id_grant_start")
    #     # start_date.send_keys("2022-11-01")
    #     # end_date = driver.find_element_by_id("id_grant_end")
    #     # end_date.send_keys("2025-11-01")
    #     # credit = driver.find_element_by_id("id_percent_credit")
    #     # credit.send_keys("10")
    #     # funding = driver.find_element_by_id("id_direct_funding")
    #     # funding.send_keys("1000")
    #     # award = driver.find_element_by_id("id_total_amount_awarded")
    #     # award.send_keys("10000")
    #     # status = Select(driver.find_element_by_id("id_status"))
    #     # status.select_by_value("1")
    #     # submit_grant = driver.find_element_by_id("grant_save")
    #     # submit_grant.click()
    #     # print("\nGrant added successfully.")

    #     # del_button = driver.find_element_by_id("delete_grant")
    #     # del_button.click()
    #     # all_grants = driver.find_element_by_id("selectAll")
    #     # for element in all_grants:
    #     #     element.click()
    #     # submit_delete_g = driver.find_element_by_id("delete_grants")
    #     # submit_delete_g.click()
    #     # print("\nGrant deleted successfully.")

    #     # assert driver.current_url.__contains__("project")

    # # tests reviewing project for pi
    #     driver.get('http://127.0.0.1:8000/project/1/review')
    #     if (driver.title.__contains__("Review")):
    #         reason = driver.find_element_by_id("id_reason")
    #         reason.send_keys("N/A")
    #         acknowledgement = driver.find_element_by_id("id_acknowledgement")
    #         acknowledgement.click()
    #         submit = driver.find_element_by_id("submit_review")
    #         submit.click()
    #         print("\nProject reviewed successfully.")

    # # tests requesting allocation change for pi
    #     if (driver.find_element_by_id("hamburger_icon").is_displayed()):
    #         driver.find_element_by_id("hamburger_icon").click()

    #     driver.find_element_by_id("project_dropdown").click()
    #     driver.find_element_by_id("navbar-allocation").click()

    #     driver.get('http://127.0.0.1:8000/allocation/1')

    #     change_button = driver.find_element_by_id("request_change")
    #     change_button.click()

    #     extension = Select(driver.find_element_by_id("id_end_date_extension"))
    #     extension.select_by_value("30")
    #     change_justification = driver.find_element_by_id("id_justification")
    #     change_justification.send_keys("This is a test justification.")
    #     submit_change = driver.find_element_by_id("submit_change")
    #     submit_change.click()
    #     print("\nAllocation change submitted successfully.")

    #     assert driver.current_url.__contains__("allocation")

    #     # tests renewing allocation -- find a way to make allocation active but expiring in less than 60 days

    #     driver.close()

class AdminTests(LiveServerTestCase):

    global driver
    driver = webdriver.Chrome()
    driver.get('http://127.0.0.1:8000/')

    def test_admin(self):
        print("\nTesting admin controls:\n-----------------------")

        # tests pi login
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
        username.send_keys("admin")
        password.send_keys("test1234")
        driver.find_element_by_id("login").click()
        assert driver.current_url == 'http://127.0.0.1:8000/'
        print("\nLogged in successfully.")

        #tests approving allocation request
        if (driver.find_element_by_id("hamburger_icon").is_displayed()):
            driver.find_element_by_id("hamburger_icon").click()

        driver.find_element_by_id("admin_dropdown").click()
        request_button = driver.find_element_by_id("navbar-allocation-requests")
        request_button.click()

        #find request button

        driver.close()