from django.test import TestCase

from django.test import LiveServerTestCase
from selenium import webdriver

# Create your tests here.

class LoginTest(LiveServerTestCase):

    def testlogin(self):
        driver = webdriver.Chrome()

        driver.get('http://127.0.0.1:8000/')

        assert 'Welcome' in driver.title
