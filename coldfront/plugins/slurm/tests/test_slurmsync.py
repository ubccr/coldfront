from io import StringIO
import datetime
from dateutil.relativedelta import relativedelta
import sys

from django.core.management import call_command
from django.test import TestCase

from coldfront.core.resource.models import Resource

from coldfront.plugins.slurm.associations import (
        SlurmCluster,
        SlurmBase,
        )

from coldfront.plugins.slurm.utils import (
        SLURM_CLUSTER_ATTRIBUTE_NAME,
        SLURM_ACCOUNT_ATTRIBUTE_NAME,
        SLURM_SPECS_ATTRIBUTE_NAME,
        SLURM_USER_SPECS_ATTRIBUTE_NAME,
        )

TEST_CLUSTER_NAME='SlurmSync Test Cluster'

# Expected test results
EXP_ADD_SPIDERMAN="""/usr/bin/sacctmgr -Q -i create user name=spiderman cluster=synctest account=superhero_alloc maxjobs=5 maxjobsaccrue=5
""".rstrip()

EXP_DEL_TEDDYR="""/usr/bin/sacctmgr -Q -i delete user where name=teddyr cluster=synctest account=amexp_alloc
""".rstrip()

EXP_MOD_BOND_FULL="""/usr/bin/sacctmgr -Q -i modify user where cluster=synctest account=superhero_alloc user=bond007 set maxjobs=5 maxjobsaccrue=5
""".rstrip()

EXP_MOD_BOND_NOMAXJOBS="""/usr/bin/sacctmgr -Q -i modify user where cluster=synctest account=superhero_alloc user=bond007 set maxjobsaccrue=5
""".rstrip()

EXP_ADD_AMEXP_FULL="""/usr/bin/sacctmgr -Q -i create account name=amexp_alloc cluster=synctest grpjob=20 grptres=nodes=10,mem=200000 grptresmins=cpu=1000000
/usr/bin/sacctmgr -Q -i create user name=gwash cluster=synctest account=amexp_alloc maxjobs=5 maxjobsaccrue=5
/usr/bin/sacctmgr -Q -i create user name=lincoln cluster=synctest account=amexp_alloc maxjobs=5 maxjobsaccrue=5
""".rstrip()

EXP_ADD_AMEXP_NOUSERS="""/usr/bin/sacctmgr -Q -i create account name=amexp_alloc cluster=synctest grpjob=20 grptres=nodes=10,mem=200000 grptresmins=cpu=1000000
""".rstrip()

EXP_DEL_STOOGES="""/usr/bin/sacctmgr -Q -i delete user where name=larry cluster=synctest account=stooges_alloc
/usr/bin/sacctmgr -Q -i delete user where name=mo cluster=synctest account=stooges_alloc
/usr/bin/sacctmgr -Q -i delete user where name=curly cluster=synctest account=stooges_alloc
/usr/bin/sacctmgr -Q -i delete account where name=stooges_alloc cluster=synctest
""".rstrip()

EXP_MOD_HEROS_FULL="""/usr/bin/sacctmgr -Q -i modify account where cluster=synctest account=superhero_alloc set grpjob=20 grptres=nodes=10 grptresmins=cpu=5000000
""".rstrip()

EXP_MOD_HEROS_NOGRPJOB="""/usr/bin/sacctmgr -Q -i modify account where cluster=synctest account=superhero_alloc set grptres=nodes=10 grptresmins=cpu=5000000
""".rstrip()

EXP_MOD_HEROS_NOGRPTRES="""/usr/bin/sacctmgr -Q -i modify account where cluster=synctest account=superhero_alloc set grpjob=20 grptresmins=cpu=5000000
""".rstrip()

EXP_MOD_HEROS_NOGRPTRESMINS="""/usr/bin/sacctmgr -Q -i modify account where cluster=synctest account=superhero_alloc set grpjob=20 grptres=nodes=10
""".rstrip()

EXP_ADD_SYNCTEST_FULL="""/usr/bin/sacctmgr -Q -i create cluster name=synctest 
/usr/bin/sacctmgr -Q -i create account name=root cluster=synctest
/usr/bin/sacctmgr -Q -i create account name=amexp_alloc cluster=synctest grpjob=20 grptres=nodes=10,mem=200000 grptresmins=cpu=1000000
/usr/bin/sacctmgr -Q -i create user name=gwash cluster=synctest account=amexp_alloc maxjobs=5 maxjobsaccrue=5
/usr/bin/sacctmgr -Q -i create user name=lincoln cluster=synctest account=amexp_alloc maxjobs=5 maxjobsaccrue=5
/usr/bin/sacctmgr -Q -i create account name=superhero_alloc cluster=synctest grpjob=20 grptres=nodes=10,mem=200000 grptresmins=cpu=5000000
/usr/bin/sacctmgr -Q -i create user name=superman cluster=synctest account=superhero_alloc maxjobs=5 maxjobsaccrue=5
/usr/bin/sacctmgr -Q -i create user name=bond007 cluster=synctest account=superhero_alloc maxjobs=5 maxjobsaccrue=5
/usr/bin/sacctmgr -Q -i create user name=spiderman cluster=synctest account=superhero_alloc maxjobs=5 maxjobsaccrue=5
""".rstrip()

EXP_ADD_SYNCTEST_NOACCT="""/usr/bin/sacctmgr -Q -i create cluster name=synctest 
""".rstrip()

EXP_ADD_SYNCTEST_NOUSER="""/usr/bin/sacctmgr -Q -i create cluster name=synctest 
/usr/bin/sacctmgr -Q -i create account name=root cluster=synctest
/usr/bin/sacctmgr -Q -i create account name=amexp_alloc cluster=synctest grpjob=20 grptres=nodes=10,mem=200000 grptresmins=cpu=1000000
/usr/bin/sacctmgr -Q -i create account name=superhero_alloc cluster=synctest grpjob=20 grptres=nodes=10,mem=200000 grptresmins=cpu=5000000
""".rstrip()

EXP_DEL_SYNCTEST_FULL="""/usr/bin/sacctmgr -Q -i delete user where name=gwash cluster=synctest account=amexp_alloc
/usr/bin/sacctmgr -Q -i delete user where name=lincoln cluster=synctest account=amexp_alloc
/usr/bin/sacctmgr -Q -i delete account where name=amexp_alloc cluster=synctest
/usr/bin/sacctmgr -Q -i delete user where name=superman cluster=synctest account=superhero_alloc
/usr/bin/sacctmgr -Q -i delete user where name=bond007 cluster=synctest account=superhero_alloc
/usr/bin/sacctmgr -Q -i delete user where name=spiderman cluster=synctest account=superhero_alloc
/usr/bin/sacctmgr -Q -i delete account where name=superhero_alloc cluster=synctest
/usr/bin/sacctmgr -Q -i delete cluster where cluster=synctest
""".rstrip()

class SlurmSyncTest(TestCase):
    fixtures = ['slurmsync_test_data.json']
    maxDiff = None

    # Helper routines

    def get_cf_cluster(self):
        resource = Resource.objects.get(name=TEST_CLUSTER_NAME)
        cf_cluster = SlurmCluster.new_from_resource(resource, addroot=True)
        return cf_cluster

    def get_sl_cluster_from_string(self, str):
        dump = StringIO(str)
        # Parse sacctmgr dump format
        sl_cluster = SlurmCluster.new_from_stream(dump)
        return sl_cluster

    # Load various slurm dump files

    def sl_cluster_fixture(self):
        """This loads slurm config matching the fixture"""
        sl_cluster = self.get_sl_cluster_from_string("""
# This should match the test slurmsync_test_data.json test fixture
Cluster - 'synctest':
Parent - 'root'
Account - 'amexp_alloc':GrpTRES=nodes=10,mem=200000:GrpTRESMins=cpu=1000000:GrpJob=20
Parent - 'root'
Account - 'superhero_alloc':GrpTRES=nodes=10,mem=200000:GrpTRESMins=cpu=5000000:GrpJob=20
Parent - 'root'
Parent - 'amexp_alloc'
User - 'gwash':MaxJobsAccrue=5:MaxJobs=5
User - 'lincoln':MaxJobsAccrue=5:MaxJobs=5
Parent - 'superhero_alloc'
User - 'superman':MaxJobsAccrue=5:MaxJobs=5
User - 'bond007':MaxJobsAccrue=5:MaxJobs=5
User - 'spiderman':MaxJobsAccrue=5:MaxJobs=5
        """)
        return sl_cluster

    def sl_cluster_fixture_no_spiderman(self):
        """This loads config missing user spiderman"""
        sl_cluster = self.get_sl_cluster_from_string("""
# This is missing spiderman
Cluster - 'synctest':
Parent - 'root'
Account - 'amexp_alloc':GrpTRES=nodes=10,mem=200000:GrpTRESMins=cpu=1000000:GrpJob=20
Parent - 'root'
Account - 'superhero_alloc':GrpTRES=nodes=10,mem=200000:GrpTRESMins=cpu=5000000:GrpJob=20
Parent - 'root'
Parent - 'amexp_alloc'
User - 'gwash':MaxJobsAccrue=5:MaxJobs=5
User - 'lincoln':MaxJobsAccrue=5:MaxJobs=5
Parent - 'superhero_alloc'
User - 'superman':MaxJobsAccrue=5:MaxJobs=5
User - 'bond007':MaxJobsAccrue=5:MaxJobs=5
        """)
        return sl_cluster

    def sl_cluster_fixture_plus_teddyr(self):
        """This loads config with extra user teddyr"""
        sl_cluster = self.get_sl_cluster_from_string("""
# This has Teddy Rooselvelt added
Cluster - 'synctest':
Parent - 'root'
Account - 'amexp_alloc':GrpTRES=nodes=10,mem=200000:GrpTRESMins=cpu=1000000:GrpJob=20
Parent - 'root'
Account - 'superhero_alloc':GrpTRES=nodes=10,mem=200000:GrpTRESMins=cpu=5000000:GrpJob=20
Parent - 'root'
Parent - 'amexp_alloc'
User - 'gwash':MaxJobsAccrue=5:MaxJobs=5
User - 'teddyr':MaxJobsAccrue=5:MaxJobs=5
User - 'lincoln':MaxJobsAccrue=5:MaxJobs=5
Parent - 'superhero_alloc'
User - 'superman':MaxJobsAccrue=5:MaxJobs=5
User - 'bond007':MaxJobsAccrue=5:MaxJobs=5
User - 'spiderman':MaxJobsAccrue=5:MaxJobs=5
        """)
        return sl_cluster

    def sl_cluster_fixture_modified007(self):
        """This loads config with bond007 account modified"""
        sl_cluster = self.get_sl_cluster_from_string("""
# This gives 007 7 MaxJobs, MaxJobsAccrue
Cluster - 'synctest':
Parent - 'root'
Account - 'amexp_alloc':GrpTRES=nodes=10,mem=200000:GrpTRESMins=cpu=1000000:GrpJob=20
Parent - 'root'
Account - 'superhero_alloc':GrpTRES=nodes=10,mem=200000:GrpTRESMins=cpu=5000000:GrpJob=20
Parent - 'root'
Parent - 'amexp_alloc'
User - 'gwash':MaxJobsAccrue=5:MaxJobs=5
User - 'lincoln':MaxJobsAccrue=5:MaxJobs=5
Parent - 'superhero_alloc'
User - 'superman':MaxJobsAccrue=5:MaxJobs=5
User - 'bond007':MaxJobsAccrue=7:MaxJobs=7
User - 'spiderman':MaxJobsAccrue=5:MaxJobs=5
        """)
        return sl_cluster

    def sl_cluster_fixture_no_amexp(self):
        """This loads slurm with amexp alloc and users missing"""
        sl_cluster = self.get_sl_cluster_from_string("""
# This should match the test slurmsync_test_data.json test fixture
Cluster - 'synctest':
Parent - 'root'
Account - 'superhero_alloc':GrpTRES=nodes=10,mem=200000:GrpTRESMins=cpu=5000000:GrpJob=20
Parent - 'root'
Parent - 'superhero_alloc'
User - 'superman':MaxJobsAccrue=5:MaxJobs=5
User - 'bond007':MaxJobsAccrue=5:MaxJobs=5
User - 'spiderman':MaxJobsAccrue=5:MaxJobs=5
        """)
        return sl_cluster

    def sl_cluster_fixture_plus_stooges(self):
        """This loads slurm config with stooges alloc/users added"""
        sl_cluster = self.get_sl_cluster_from_string("""
# This should match the test slurmsync_test_data.json test fixture
Cluster - 'synctest':
Parent - 'root'
Account - 'amexp_alloc':GrpTRES=nodes=10,mem=200000:GrpTRESMins=cpu=1000000:GrpJob=20
Parent - 'root'
Account - 'superhero_alloc':GrpTRES=nodes=10,mem=200000:GrpTRESMins=cpu=5000000:GrpJob=20
Parent - 'root'
Account - 'stooges_alloc':GrpTRES=nodes=10,mem=200000:GrpTRESMins=cpu=5000000:GrpJob=20
Parent - 'root'
Parent - 'amexp_alloc'
User - 'gwash':MaxJobsAccrue=5:MaxJobs=5
User - 'lincoln':MaxJobsAccrue=5:MaxJobs=5
Parent - 'superhero_alloc'
User - 'superman':MaxJobsAccrue=5:MaxJobs=5
User - 'bond007':MaxJobsAccrue=5:MaxJobs=5
User - 'spiderman':MaxJobsAccrue=5:MaxJobs=5
Parent - 'stooges_alloc'
User - 'larry':MaxJobsAccrue=5:MaxJobs=5
User - 'mo':MaxJobsAccrue=5:MaxJobs=5
User - 'curly':MaxJobsAccrue=5:MaxJobs=5
        """)
        return sl_cluster

    def sl_cluster_fixture_modified_heros(self):
        """This loads slurm config with modified superheros allocation"""
        sl_cluster = self.get_sl_cluster_from_string("""
# This should match the test slurmsync_test_data.json test fixture
Cluster - 'synctest':
Parent - 'root'
Account - 'amexp_alloc':GrpTRES=nodes=10,mem=200000:GrpTRESMins=cpu=1000000:GrpJob=20
Parent - 'root'
Account - 'superhero_alloc':GrpTRES=nodes=20,mem=200000:GrpTRESMins=cpu=7000000:GrpJob=30
Parent - 'root'
Parent - 'amexp_alloc'
User - 'gwash':MaxJobsAccrue=5:MaxJobs=5
User - 'lincoln':MaxJobsAccrue=5:MaxJobs=5
Parent - 'superhero_alloc'
User - 'superman':MaxJobsAccrue=5:MaxJobs=5
User - 'bond007':MaxJobsAccrue=5:MaxJobs=5
User - 'spiderman':MaxJobsAccrue=5:MaxJobs=5
        """)
        return sl_cluster

    ########################################################################
    #                       Tests
    ########################################################################

    # Test low-level spec routines

    def test_spec_routines_nospecs(self):
        testname='spec routines, nospecs'
        sbase = SlurmBase(name='Test', specs=None)
        fmtd_specs = sbase.format_specs()
        spec_dict = sbase.spec_dict()
        with self.subTest(msg=testname, spec=''):
            self.assertEqual(fmtd_specs,'')
            self.assertEqual(spec_dict, {})

    def test_spec_routines_tres(self):
        testname='spec routines, TRES'
        sbase = SlurmBase(name='Test', specs=None)
        fmtd_specs = sbase.format_specs()
        spec_dict = sbase.spec_dict()
        spec = 'GrpJob=20:GrpTRES=nodes=10,mem=200000:GrpTRESMins=cpu=1000000'
        specs = spec.split(':')
        exp_dict = {
                'grpjob': '20',
                'grptres': { 'nodes':'10', 'mem':'200000' },
                'grptresmins': { 'cpu':'1000000' },
                }
        fmtd_specs = sbase.format_specs(specs=specs)
        spec_dict = sbase.spec_dict(specs=specs)
        with self.subTest(msg=testname, spec=spec):
            self.assertEqual(fmtd_specs,spec)
            self.assertEqual(spec_dict, exp_dict)

    # Higher level tests: load a slurm flatfile dump and compare to DB

    def test_noop(self):
        """Test that if cluster unchanged, no changes attempted"""
        cf_cluster = self.get_cf_cluster()
        sl_cluster = self.sl_cluster_fixture()
        expected=''

        # Input cluster config same as DB, should produce no changes
        output = cf_cluster.update_cluster_to(
                old=sl_cluster,
                new=cf_cluster,
                noop=True,
                noout=True).rstrip()
        self.assertEqual(output, expected,
                msg="No changes should produce no output")

    def test_adduser_noflags(self):
        """Tests when need to add an user, with no flags"""
        cf_cluster = self.get_cf_cluster()
        sl_cluster = self.sl_cluster_fixture_no_spiderman()

        # No flags, should add user
        expected = EXP_ADD_SPIDERMAN
        output = cf_cluster.update_cluster_to(
                old=sl_cluster,
                new=cf_cluster,
                noop=True,
                noout=True).rstrip()
        self.assertEqual(output, expected)

    def test_adduser_skip_create_user(self):
        """Tests when need to add an user, with flags=skip_create_user"""
        cf_cluster = self.get_cf_cluster()
        sl_cluster = self.sl_cluster_fixture_no_spiderman()

        # With skip_create_user should not make any changes
        flags= ['skip_create_user' ]
        expected = ''
        output = cf_cluster.update_cluster_to(
                old=sl_cluster,
                new=cf_cluster,
                flags=flags,
                noop=True,
                noout=True).rstrip()
        self.assertEqual(output, expected)


    def test_adduser_ignore_maxjobs(self):
        """Tests when need to add an user, with flags=ignore_maxjobs"""
        cf_cluster = self.get_cf_cluster()
        sl_cluster = self.sl_cluster_fixture_no_spiderman()

        # Should still do full add with spec flags
        flags= [ 'ignore_maxjobs' ]
        expected = EXP_ADD_SPIDERMAN
        output = cf_cluster.update_cluster_to(
                old=sl_cluster,
                new=cf_cluster,
                flags=flags,
                noop=True,
                noout=True).rstrip()
        self.assertEqual(output, expected)

    def test_deluser_noflags(self):
        cf_cluster = self.get_cf_cluster()
        sl_cluster = self.sl_cluster_fixture_plus_teddyr()

        # No flags, should delete user
        expected = EXP_DEL_TEDDYR
        output = cf_cluster.update_cluster_to(
                old=sl_cluster,
                new=cf_cluster,
                noop=True,
                noout=True).rstrip()
        self.assertEqual(output, expected)

    def test_deluser_skip_delete_user(self):
        cf_cluster = self.get_cf_cluster()
        sl_cluster = self.sl_cluster_fixture_plus_teddyr()

        # skip_delete_user; should ignore deletion of teddy
        flags='skip_delete_user'
        expected = ''
        output = cf_cluster.update_cluster_to(
                old=sl_cluster,
                new=cf_cluster,
                flags=flags,
                noop=True,
                noout=True).rstrip()
        self.assertEqual(output, expected)

    def test_deluser_ignore_maxjobs(self):
        cf_cluster = self.get_cf_cluster()
        sl_cluster = self.sl_cluster_fixture_plus_teddyr()

        # should do normal delete regardless of spec flags
        flags='ignore_MaxJobs'
        expected = EXP_DEL_TEDDYR
        output = cf_cluster.update_cluster_to(
                old=sl_cluster,
                new=cf_cluster,
                flags=flags,
                noop=True,
                noout=True).rstrip()
        self.assertEqual(output, expected)


    def test_moduser_noflags(self):
        cf_cluster = self.get_cf_cluster()
        sl_cluster = self.sl_cluster_fixture_modified007()

        # No flags, just modify user to make identical
        expected = EXP_MOD_BOND_FULL
        output = cf_cluster.update_cluster_to(
                old=sl_cluster,
                new=cf_cluster,
                noop=True,
                noout=True).rstrip()
        self.assertEqual(output, expected)

    def test_moduser_skip_user_specs(self):
        cf_cluster = self.get_cf_cluster()
        sl_cluster = self.sl_cluster_fixture_modified007()

        # Test skip_user_specs flag, should ignore changes in bond
        flags  = ['skip_user_specs' ]
        expected = ''
        output = cf_cluster.update_cluster_to(
                old=sl_cluster,
                new=cf_cluster,
                flags=flags,
                noop=True,
                noout=True).rstrip()
        self.assertEqual(output, expected)

    def test_moduser_ignore_maxjobs(self):
        cf_cluster = self.get_cf_cluster()
        sl_cluster = self.sl_cluster_fixture_modified007()

        # Test ignore_maxjobs flag, should only partially change bond
        flags  = ['ignore_maxjobs' ]
        expected = EXP_MOD_BOND_NOMAXJOBS
        output = cf_cluster.update_cluster_to(
                old=sl_cluster,
                new=cf_cluster,
                flags=flags,
                noop=True,
                noout=True).rstrip()
        self.assertEqual(output, expected)

    def test_addacct_noflags(self):
        cf_cluster = self.get_cf_cluster()
        sl_cluster = self.sl_cluster_fixture_no_amexp()

        # Test when account needs to be added
        expected = EXP_ADD_AMEXP_FULL
        output = cf_cluster.update_cluster_to(
                old=sl_cluster,
                new=cf_cluster,
                noop=True,
                noout=True).rstrip()
        self.assertEqual(output, expected)

    def test_addacct_skip_create_account(self):
        cf_cluster = self.get_cf_cluster()
        sl_cluster = self.sl_cluster_fixture_no_amexp()

        # Test that account not created when skip_create_account
        expected = ''
        flags  = ['skip_create_account' ]
        output = cf_cluster.update_cluster_to(
                old=sl_cluster,
                new=cf_cluster,
                flags=flags,
                noop=True,
                noout=True).rstrip()
        self.assertEqual(output, expected)

    def test_addacct_skip_account_specs(self):
        cf_cluster = self.get_cf_cluster()
        sl_cluster = self.sl_cluster_fixture_no_amexp()

        # Should still add account in full with skip_account_specs
        expected = EXP_ADD_AMEXP_FULL
        flags  = ['skip_account_specs' ]
        output = cf_cluster.update_cluster_to(
                old=sl_cluster,
                new=cf_cluster,
                flags=flags,
                noop=True,
                noout=True).rstrip()
        self.assertEqual(output, expected)

    def test_addacct_skip_create_user(self):
        cf_cluster = self.get_cf_cluster()
        sl_cluster = self.sl_cluster_fixture_no_amexp()

        # Should add account but not users
        expected = EXP_ADD_AMEXP_NOUSERS
        flags  = ['skip_create_user' ]
        output = cf_cluster.update_cluster_to(
                old=sl_cluster,
                new=cf_cluster,
                flags=flags,
                noop=True,
                noout=True).rstrip()
        self.assertEqual(output, expected)

    def test_delacct_noflags(self):
        cf_cluster = self.get_cf_cluster()
        sl_cluster = self.sl_cluster_fixture_plus_stooges()

        # Should delete users then account
        expected = EXP_DEL_STOOGES
        output = cf_cluster.update_cluster_to(
                old=sl_cluster,
                new=cf_cluster,
                noop=True,
                noout=True).rstrip()
        self.assertEqual(output, expected)

    def test_delacct_skip_delete_account(self):
        cf_cluster = self.get_cf_cluster()
        sl_cluster = self.sl_cluster_fixture_plus_stooges()

        # Should skip deleting the stooges
        # skip_delete_account => skip_delete_user for users
        # of the affected account.  
        flags  = ['skip_delete_account' ]
        expected = ''
        output = cf_cluster.update_cluster_to(
                old=sl_cluster,
                new=cf_cluster,
                flags=flags,
                noop=True,
                noout=True).rstrip()
        self.assertEqual(output, expected)

    def test_delacct_skip_delete_user(self):
        cf_cluster = self.get_cf_cluster()
        sl_cluster = self.sl_cluster_fixture_plus_stooges()

        # Should still do full delete, including users
        flags  = ['skip_delete_user' ]
        expected = EXP_DEL_STOOGES
        output = cf_cluster.update_cluster_to(
                old=sl_cluster,
                new=cf_cluster,
                flags=flags,
                noop=True,
                noout=True).rstrip()
        self.assertEqual(output, expected)

    def test_delacct_skip_cluster_specs(self):
        cf_cluster = self.get_cf_cluster()
        sl_cluster = self.sl_cluster_fixture_plus_stooges()

        # Should still do full delete, including users
        flags  = ['skip_cluster_specs' ]
        expected = EXP_DEL_STOOGES
        output = cf_cluster.update_cluster_to(
                old=sl_cluster,
                new=cf_cluster,
                flags=flags,
                noop=True,
                noout=True).rstrip()
        self.assertEqual(output, expected)

    def test_delacct_ignore_grpjob(self):
        cf_cluster = self.get_cf_cluster()
        sl_cluster = self.sl_cluster_fixture_plus_stooges()

        # Should still do full delete, including users
        flags  = ['ignore_grpjob' ]
        expected = EXP_DEL_STOOGES
        output = cf_cluster.update_cluster_to(
                old=sl_cluster,
                new=cf_cluster,
                flags=flags,
                noop=True,
                noout=True).rstrip()
        self.assertEqual(output, expected)

    def test_modacct_noflags(self):
        cf_cluster = self.get_cf_cluster()
        sl_cluster = self.sl_cluster_fixture_modified_heros()

        # Should get full modification
        expected = EXP_MOD_HEROS_FULL
        output = cf_cluster.update_cluster_to(
                old=sl_cluster,
                new=cf_cluster,
                noop=True,
                noout=True).rstrip()
        self.assertEqual(output, expected)

    def test_modacct_skip_account_specs(self):
        cf_cluster = self.get_cf_cluster()
        sl_cluster = self.sl_cluster_fixture_modified_heros()

        # Should show no changes
        expected = ''
        flags  = ['skip_account_specs' ]
        output = cf_cluster.update_cluster_to(
                old=sl_cluster,
                new=cf_cluster,
                flags=flags,
                noop=True,
                noout=True).rstrip()
        self.assertEqual(output, expected)

    def test_modacct_skip_account_specs(self):
        cf_cluster = self.get_cf_cluster()
        sl_cluster = self.sl_cluster_fixture_modified_heros()

        # Should show no changes
        expected = ''
        flags  = ['skip_account_specs' ]
        output = cf_cluster.update_cluster_to(
                old=sl_cluster,
                new=cf_cluster,
                flags=flags,
                noop=True,
                noout=True).rstrip()
        self.assertEqual(output, expected)

    def test_modacct_skip_account_specs(self):
        cf_cluster = self.get_cf_cluster()
        sl_cluster = self.sl_cluster_fixture_modified_heros()

        # Should show no changes
        expected = ''
        flags  = ['skip_account_specs' ]
        output = cf_cluster.update_cluster_to(
                old=sl_cluster,
                new=cf_cluster,
                flags=flags,
                noop=True,
                noout=True).rstrip()
        self.assertEqual(output, expected)

    def test_modacct_ignore_grpjob(self):
        cf_cluster = self.get_cf_cluster()
        sl_cluster = self.sl_cluster_fixture_modified_heros()

        # Should show changes w/out grpjob changes
        expected = EXP_MOD_HEROS_NOGRPJOB
        flags  = ['ignore_grpjob' ]
        output = cf_cluster.update_cluster_to(
                old=sl_cluster,
                new=cf_cluster,
                flags=flags,
                noop=True,
                noout=True).rstrip()
        self.assertEqual(output, expected)

    def test_modacct_ignore_grptresmins(self):
        cf_cluster = self.get_cf_cluster()
        sl_cluster = self.sl_cluster_fixture_modified_heros()

        # Should show changes except in grptresmin
        expected = EXP_MOD_HEROS_NOGRPTRESMINS
        flags  = ['ignore_grptresmins' ]
        output = cf_cluster.update_cluster_to(
                old=sl_cluster,
                new=cf_cluster,
                flags=flags,
                noop=True,
                noout=True).rstrip()
        self.assertEqual(output, expected)


    def test_modacct_ignore_grptresmins_cpu(self):
        cf_cluster = self.get_cf_cluster()
        sl_cluster = self.sl_cluster_fixture_modified_heros()

        # Should show changes except in grptresmins_cpu
        expected = EXP_MOD_HEROS_NOGRPTRESMINS
        flags  = ['ignore_grptresmins_cpu' ]
        output = cf_cluster.update_cluster_to(
                old=sl_cluster,
                new=cf_cluster,
                flags=flags,
                noop=True,
                noout=True).rstrip()
        self.assertEqual(output, expected)

    def test_modacct_ignore_grptres(self):
        cf_cluster = self.get_cf_cluster()
        sl_cluster = self.sl_cluster_fixture_modified_heros()

        # Should show changes except in grptres
        expected = EXP_MOD_HEROS_NOGRPTRES
        flags  = ['ignore_grptres' ]
        output = cf_cluster.update_cluster_to(
                old=sl_cluster,
                new=cf_cluster,
                flags=flags,
                noop=True,
                noout=True).rstrip()
        self.assertEqual(output, expected)

    def test_modacct_ignore_grptres_nodes(self):
        cf_cluster = self.get_cf_cluster()
        sl_cluster = self.sl_cluster_fixture_modified_heros()

        # Should show changes except in grptres
        expected = EXP_MOD_HEROS_NOGRPTRES
        flags  = ['ignore_grptres_nodes' ]
        output = cf_cluster.update_cluster_to(
                old=sl_cluster,
                new=cf_cluster,
                flags=flags,
                noop=True,
                noout=True).rstrip()
        self.assertEqual(output, expected)

    def test_modacct_ignore_grptres_mem(self):
        cf_cluster = self.get_cf_cluster()
        sl_cluster = self.sl_cluster_fixture_modified_heros()

        # Should show full changes (as grptres_mem was not changed)
        expected = EXP_MOD_HEROS_FULL
        flags  = ['ignore_grptres_mem' ]
        output = cf_cluster.update_cluster_to(
                old=sl_cluster,
                new=cf_cluster,
                flags=flags,
                noop=True,
                noout=True).rstrip()
        self.assertEqual(output, expected)

    def test_modacct_ignore_grptres_grptresmins_grpjob(self):
        cf_cluster = self.get_cf_cluster()
        sl_cluster = self.sl_cluster_fixture_modified_heros()

        # Should show no changes
        expected = ''
        flags  = ['ignore_grptres', 'ignore_grptresmins', 'ignore_grpjob' ]
        output = cf_cluster.update_cluster_to(
                old=sl_cluster,
                new=cf_cluster,
                flags=flags,
                noop=True,
                noout=True).rstrip()
        self.assertEqual(output, expected)

    def test_modacct_ignore_grptres_nodes_grptresmins_grpjob(self):
        cf_cluster = self.get_cf_cluster()
        sl_cluster = self.sl_cluster_fixture_modified_heros()

        # Should show no changes
        expected = ''
        flags  = ['ignore_grptres_nodes', 'ignore_grptresmins', 'ignore_grpjob' ]
        output = cf_cluster.update_cluster_to(
                old=sl_cluster,
                new=cf_cluster,
                flags=flags,
                noop=True,
                noout=True).rstrip()
        self.assertEqual(output, expected)

    def test_addcluster_skip_create_cluster(self):
        cf_cluster = self.get_cf_cluster()
        #To get an empty cluster, we need to set sl_cluster to None
        sl_cluster = None

        # Should show no changes
        flags  = ['skip_create_cluster' ]
        expected = ''
        output = cf_cluster.update_cluster_to(
                old=sl_cluster,
                new=cf_cluster,
                flags=flags,
                noop=True,
                noout=True).rstrip()
        self.assertEqual(output, expected)

    def test_addcluster_skip_create_account(self):
        cf_cluster = self.get_cf_cluster()
        #To get an empty cluster, we need to set sl_cluster to None
        sl_cluster = None

        # Should create cluster but no accounts/users
        flags  = ['skip_create_account' ]
        expected = EXP_ADD_SYNCTEST_NOACCT
        output = cf_cluster.update_cluster_to(
                old=sl_cluster,
                new=cf_cluster,
                flags=flags,
                noop=True,
                noout=True).rstrip()
        self.assertEqual(output, expected)

    def test_addcluster_skip_create_user(self):
        cf_cluster = self.get_cf_cluster()
        #To get an empty cluster, we need to set sl_cluster to None
        sl_cluster = None

        # Should create cluster/accounts but no users
        flags  = ['skip_create_user' ]
        expected = EXP_ADD_SYNCTEST_NOUSER
        output = cf_cluster.update_cluster_to(
                old=sl_cluster,
                new=cf_cluster,
                flags=flags,
                noop=True,
                noout=True).rstrip()
        self.assertEqual(output, expected)

    def test_addcluster_noflags(self):
        cf_cluster = self.get_cf_cluster()
        #To get an empty cluster, we need to set sl_cluster to None
        sl_cluster = None

        # Should create complete cluster
        expected = EXP_ADD_SYNCTEST_FULL
        output = cf_cluster.update_cluster_to(
                old=sl_cluster,
                new=cf_cluster,
                noop=True,
                noout=True).rstrip()
        self.assertEqual(output, expected)

    def test_delcluster_noflags(self):
        #To get an empty cluster, we need to set sl_cluster to None
        cf_cluster = None
        sl_cluster = self.sl_cluster_fixture()

        # Should not do anything as force_delete_cluster not set
        expected = ''
        output = sl_cluster.update_cluster_to(
                old=sl_cluster,
                new=cf_cluster,
                noop=True,
                noout=True).rstrip()
        self.assertEqual(output, expected)

    def test_delcluster_force_delete_cluster_skip_delete_cluster(self):
        #To get an empty cluster, we need to set sl_cluster to None
        cf_cluster = None
        sl_cluster = self.sl_cluster_fixture()

        # Should not do anything as skip_delete_cluster set
        flags  = ['skip_delete_cluster', 'force_delete_cluster' ]
        expected = ''
        output = sl_cluster.update_cluster_to(
                old=sl_cluster,
                new=cf_cluster,
                flags=flags,
                noop=True,
                noout=True).rstrip()
        self.assertEqual(output, expected)

    def test_delcluster_force_delete_cluster(self):
        #To get an empty cluster, we need to set sl_cluster to None
        cf_cluster = None
        sl_cluster = self.sl_cluster_fixture()

        # Should fully delete cluster as has force_delete_cluster
        flags  = [ 'force_delete_cluster' ]
        expected = EXP_DEL_SYNCTEST_FULL
        output = sl_cluster.update_cluster_to(
                old=sl_cluster,
                new=cf_cluster,
                flags=flags,
                noop=True,
                noout=True).rstrip()
        self.assertEqual(output, expected)

    def test_delcluster_force_delete_cluster_skip_delete_account(self):
        #To get an empty cluster, we need to set sl_cluster to None
        cf_cluster = None
        sl_cluster = self.sl_cluster_fixture()

        # Should fully delete cluster; skip_delete_account ignored
        flags  = [ 'force_delete_cluster', 'skip_delete_account' ]
        expected = EXP_DEL_SYNCTEST_FULL
        output = sl_cluster.update_cluster_to(
                old=sl_cluster,
                new=cf_cluster,
                flags=flags,
                noop=True,
                noout=True).rstrip()
        self.assertEqual(output, expected)

    def test_delcluster_force_delete_cluster_skip_delete_user(self):
        #To get an empty cluster, we need to set sl_cluster to None
        cf_cluster = None
        sl_cluster = self.sl_cluster_fixture()

        # Should fully delete cluster; skip_delete_user ignored
        flags  = [ 'force_delete_cluster', 'skip_delete_user' ]
        expected = EXP_DEL_SYNCTEST_FULL
        output = sl_cluster.update_cluster_to(
                old=sl_cluster,
                new=cf_cluster,
                flags=flags,
                noop=True,
                noout=True).rstrip()
        self.assertEqual(output, expected)

