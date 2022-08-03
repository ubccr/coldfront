import os
import unittest

from coldfront.plugins.sftocf.pipeline import *

class PipelineTests(unittest.TestCase):


    def test_generate_serv_vol_dict(self):
        v1 = {'holylfs04', 'holylfs05', 'holy-isilon'}
        e1 = {"holysfdb01": {"holylfs04":"HDD/C/LABS",'holylfs05':"C/LABS",},
        "holysfdb02": {"holy-isilon":"rc_labs"}}
        assert generate_serv_vol_dict(v1) == e1

        v2 = {'holylfs04', 'holylfs05'}
        e2 = {"holysfdb01": {"holylfs04":"HDD/C/LABS",'holylfs05':"C/LABS",}}
        assert generate_serv_vol_dict(v2) == e2

    def test_use_zone(self):
        assert not use_zone("name")
