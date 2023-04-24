from datetime import datetime
import pandas as pd

from ldap3.core.timezone import OffsetTzInfo
from django.test import TestCase, tag
from django.contrib.auth import get_user_model

from coldfront.plugins.ldap.utils import (format_template_assertions,
                                        LDAPConn,
                                        GroupUserCollection,
                                        add_new_projects)


FIXTURES = [
        'coldfront/core/test_helpers/test_data/test_fixtures/resources.json',
        'coldfront/core/test_helpers/test_data/test_fixtures/poisson_fixtures.json',
        'coldfront/core/test_helpers/test_data/test_fixtures/admin_fixtures.json',
        'coldfront/core/test_helpers/test_data/test_fixtures/all_res_choices.json',
        'coldfront/core/test_helpers/test_data/test_fixtures/field_of_science.json',
        'coldfront/core/test_helpers/test_data/test_fixtures/project_choices.json',
        ]

class UtilFunctionTests(TestCase):

    def test_format_template_assertions_one_kv(self):
        '''Format attr_search_dict with one key-value pair into correct filter_template input
        '''
        test_data = {'company': 'FAS'}
        desired_output = '(company=FAS)'
        output = format_template_assertions(test_data)
        self.assertEqual(output, desired_output)

    def test_format_template_assertions_multi_kv(self):
        '''Format attr_search_dict with multiple key-value pairs into correct filter_template input
        '''
        test_data = {'cn': 'Bob Smith', 'company': 'FAS'}
        desired_output = '(&(cn=Bob Smith)(company=FAS))'
        output = format_template_assertions(test_data)
        self.assertEqual(output, desired_output)

    def test_format_template_assertions_list_value(self):
        '''Format attr_search_dict with list value into correct filter_template input
        '''
        test_data = {'cn': ['Bob Smith', 'Jane Doe'], 'company': 'FAS'}
        desired_output = '(&(|(cn=Bob Smith)(cn=Jane Doe))(company=FAS))'
        output = format_template_assertions(test_data)
        self.assertEqual(output, desired_output)


class LDAPConnTest(TestCase):
    '''tests for LDAPConn class'''

    @tag('net')
    def setUp(self):
        self.ldap_conn = LDAPConn()

    @tag('net')
    def test_search_group_one_kv(self):
        '''Be able to return correct group with the variables given
        '''
        attr_search_dict = {'sAMAccountName': 'rc_test_lab'}
        results = self.ldap_conn.search_groups(attr_search_dict)
        self.assertEqual(len(results), 1)

    @tag('net')
    def test_search_user_one_kv(self):
        '''Be able to return correct user with the variables given
        '''
        attr_search_dict = {'sAMAccountName': 'atestaccount'}
        results = self.ldap_conn.search_users(attr_search_dict)
        self.assertEqual(len(results), 1)

    @tag('net')
    def test_search_user_membership(self):
        '''Be able to return correct user with the variables given
        '''
        attr_search_dict = {'memberOf': 'CN=rc_test_lab,OU=RC,OU=Domain Groups,DC=rc,DC=domain'}
        results = self.ldap_conn.search_users(attr_search_dict)
        self.assertEqual(len(results), 5)

    @tag('net')
    def test_return_group_members_manager(self):
        samaccountname = 'rc_test_lab'
        result = self.ldap_conn.return_group_members_manager(samaccountname)
        self.assertEqual(result, 'no ADUser manager found')

        samaccountname = 'cepr_test_group'
        members, manager = self.ldap_conn.return_group_members_manager(samaccountname)
        self.assertEqual(len(members), 1)

class GroupUserCollectionTests(TestCase):
    '''Tests for GroupUserCollection class'''
    fixtures = FIXTURES

    def setUp(self):
        group_name = 'bortkiewicz_lab'
        self.currentuser_accountExpires = [datetime(9999, 12, 31, 23, 59, 59, 999999, tzinfo=OffsetTzInfo(offset=0, name='UTC'))]
        self.expireduser_accountExpires = [datetime(1601, 12, 31, 23, 59, 59, 999999, tzinfo=OffsetTzInfo(offset=0, name='UTC'))]
        ad_users = [
            {
                'sAMAccountName': ['ljbortkiewicz'],
                'department': ['Statistics and Probability'],
                'userAccountControl': [512],
                'accountExpires': self.currentuser_accountExpires,
            },
            {
                'sAMAccountName': ['sdpoisson'],
                'department': ['Statistics and Probability'],
                'userAccountControl': [512],
                'accountExpires': self.currentuser_accountExpires,
            },
            {
                'sAMAccountName': ['snewcomb'],
                'department': ['Statistics and Probability'],
                'userAccountControl': [512],
                'accountExpires': self.currentuser_accountExpires,
            },
        ]
        pi = {
            'sAMAccountName': ['ljbortkiewicz'],
            'department': ['Statistics and Probability'],
            'userAccountControl': [512],
            'memberOf': ['CD=non_faculty_pi'],
            'accountExpires': self.currentuser_accountExpires,
        }
        self.guc = (GroupUserCollection(group_name, ad_users, pi))

    def deactivate_pi(self):
        self.guc.pi['accountExpires'] = self.expireduser_accountExpires
        self.guc.members[0]['accountExpires'] = self.expireduser_accountExpires

    def disable_pi(self):
        self.guc.pi['userAccountControl'] = [514]
        self.guc.members[0]['userAccountControl'] = [514]

    def test_pi_is_active(self):
        self.assertEqual(self.guc.pi_is_active, True)

    def test_current_ad_users(self):
        self.assertEqual(len(self.guc.current_ad_users), 3)

    def test_pi_not_active(self):
        self.deactivate_pi()
        self.assertEqual(self.guc.pi_is_active, False)

    def test_pi_disabled(self):
        self.disable_pi()
        self.assertEqual(self.guc.pi_is_active, False)

    def test_add_new_projects(self):
        '''unexpired pi group is added'''
        added_projects, _ = add_new_projects([self.guc], { 'no_pi': [], 'not_found': [] })
        self.assertEqual(len(added_projects), 1)

    def test_add_new_projects_pi_disabled(self):
        '''group with disabled pi is not added'''
        self.disable_pi()
        added_projects, errortracker = add_new_projects([self.guc], { 'no_pi': [], 'not_found': [] })
        self.assertEqual(len(added_projects), 0)
        self.assertEqual(errortracker['no_pi'], ['bortkiewicz_lab'])

    def test_add_new_projects_pi_expired(self):
        '''group with expired pi is not added'''
        self.deactivate_pi()
        added_projects, errortracker = add_new_projects([self.guc], { 'no_pi': [], 'not_found': [] })
        self.assertEqual(len(added_projects), 0)
        self.assertEqual(errortracker['no_pi'], ['bortkiewicz_lab'])

    def test_add_new_projects_pi_not_ifxuser(self):
        '''project with a non-ifxuser pi is not added, and pi is added to the missing_users list'''
        get_user_model().objects.get(username='ljbortkiewicz').delete()
        new_projs, errortracker = add_new_projects([self.guc], { 'no_pi': [], 'not_found': [] })
        # no project added
        self.assertEqual(errortracker['no_pi'], ['bortkiewicz_lab'])
        self.assertEqual(len(new_projs), 0)
        # missing pi recorded
        missing_users_csv = './local_data/missing/missing_users.csv'
        missing_df = pd.read_csv(missing_users_csv, parse_dates=['date'])
        test_users = missing_df.loc[missing_df.username == 'ljbortkiewicz']
        self.assertEqual(len(test_users), 1)
        # remove test user from csv
        missing_df = missing_df.loc[~(missing_df.group == 'bortkiewicz_lab')]
        missing_df.to_csv(missing_users_csv, index=False)
