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

class SlurmSyncTest(TestCase):
    fixtures = ['slurmsync_test_data.json']

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

    # Tests

    def test_spec_routines(self):
        testname = 'test_spec_routines'

        sbase = SlurmBase(name='Test', specs=None)
        fmtd_specs = sbase.format_specs()
        spec_dict = sbase.spec_dict()
        with self.subTest(msg=testname, specs='<none>'):
            self.assertEqual(fmtd_specs,'')
            self.assertEqual(spec_dict, {})

        spec = 'GrpJob=20:GrpTRES=nodes=10,mem=200000:GrpTRESMins=cpu=1000000'
        specs = spec.split(':')
        exp_dict = {
                'grpjob': '20',
                'grptres': { 'nodes':'10', 'mem':'200000' },
                'grptresmins': { 'cpu':'1000000' },
                }

        fmtd_specs = sbase.format_specs(specs=specs)
        spec_dict = sbase.spec_dict(specs=specs)
        with self.subTest(msg=testname, specs=specs):
            with self.subTest(msg='{} - fmtd_specs'.format(testname), specs=specs):
                self.assertEqual(fmtd_specs,spec)
            with self.subTest(msg='{} - spec_dicts'.format(testname), specs=specs):
                self.assertEqual(spec_dict, exp_dict)




    def test_noop(self):
        cf_cluster = self.get_cf_cluster()

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

        expected=''

        output = cf_cluster.update_cluster_to(
                old=sl_cluster,
                new=cf_cluster,
                noop=True)

        self.assertEqual(output, expected,
                msg="No changes should produce no output")

    def test_adduser(self):
        cf_cluster = self.get_cf_cluster()

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
        testname = 'Add user'
        expected="""/usr/bin/sacctmgr -Q -i create user name=spiderman cluster=synctest account=superhero_alloc maxjobs=5 maxjobsaccrue=5
        """.rstrip()

        output = cf_cluster.update_cluster_to(
                old=sl_cluster,
                new=cf_cluster,
                noop=True).rstrip()

        with self.subTest(msg=testname, flags=None):
            self.assertEqual(output, expected)

        # Should ignore this
        flags= ['skip_create_user' ]

        output = cf_cluster.update_cluster_to(
                old=sl_cluster,
                new=cf_cluster,
                flags=flags,
                noop=True).rstrip()
        with self.subTest(msg=testname, flags=flags):
            self.assertEqual(output, '')

        # Should not change if we add flags
        flags='ignore_MaxJobs'

        output = cf_cluster.update_cluster_to(
                old=sl_cluster,
                new=cf_cluster,
                flags=flags,
                noop=True).rstrip()
        with self.subTest(msg=testname, flags=flags):
            self.assertEqual(output, expected)

    def test_deluser(self):
        testname='Delete user'
        cf_cluster = self.get_cf_cluster()

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

        expected="""/usr/bin/sacctmgr -Q -i delete user where name=teddyr cluster=synctest account=amexp_alloc
        """.rstrip()

        output = cf_cluster.update_cluster_to(
                old=sl_cluster,
                new=cf_cluster,
                noop=True).rstrip()

        with self.subTest(msg=testname, flags=None):
            self.assertEqual(output, expected)

        # skip_create_user should ignore this
        flags='skip_delete_user'

        output = cf_cluster.update_cluster_to(
                old=sl_cluster,
                new=cf_cluster,
                flags=flags,
                noop=True).rstrip()
        with self.subTest(msg=testname, flags=flags):
            self.assertEqual(output, '')

        # Should not change if we add flags
        flags='ignore_MaxJobs'

        output = cf_cluster.update_cluster_to(
                old=sl_cluster,
                new=cf_cluster,
                flags=flags,
                noop=True).rstrip()
        with self.subTest(msg=testname, flags=flags):
            self.assertEqual(output, expected)

    def test_moduser(self):
        testname = 'Modify user'
        cf_cluster = self.get_cf_cluster()

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

        expected="""/usr/bin/sacctmgr -Q -i modify user where cluster=synctest account=superhero_alloc user=bond007 set maxjobs=5 maxjobsaccrue=5
        """.rstrip()

        output = cf_cluster.update_cluster_to(
                old=sl_cluster,
                new=cf_cluster,
                noop=True).rstrip()

        with self.subTest(msg=testname, flags=None):
            self.assertEqual(output, expected)

        # Test skip_user_specs flag
        flags  = ['skip_user_specs' ]

        output = cf_cluster.update_cluster_to(
                old=sl_cluster,
                new=cf_cluster,
                flags=flags,
                noop=True).rstrip()
        with self.subTest(msg=testname, flags=flags):
            self.assertEqual(output, '')
        sys.stderr.write('[TPTEST] output  ="{}"  skip_user_specs\n'.format(output))
        sys.stderr.write('[TPTEST] expected="{}"  skip_user_specs\n'.format(expected))

        # Test ignore_maxjobs flag
        flags  = ['ignore_maxjobs' ]

        expected="""/usr/bin/sacctmgr -Q -i modify user where cluster=synctest account=superhero_alloc user=bond007 set maxjobsaccrue=5
        """.rstrip()
        output = cf_cluster.update_cluster_to(
                old=sl_cluster,
                new=cf_cluster,
                flags=flags,
                noop=True).rstrip()
        with self.subTest(msg=testname, flags=flags):
            self.assertEqual(output, expected)
        sys.stderr.write('[TPTEST] output  ="{}"  ignore_maxjobs\n'.format(output))
        sys.stderr.write('[TPTEST] expected="{}"  ignore_maxjobs\n'.format(expected))



