# -*- coding: utf-8 -*-

'''
Nanites Person synchronization code

Created on  2021-06-21

@author: Aaron Kitzmiller <aaron_kitzmiller@harvard.edu>
@copyright: 2021 The Presidents and Fellows of Harvard College.
All rights reserved.
@license: GPL v2.0
'''

import logging
from ifxuser.nanites import Nanite2User


logger = logging.getLogger(__name__)


class Nanite2ColdfrontUser(Nanite2User):
    '''
    Process roles for regular users (should be deactivated) and PIs
    '''
    def setUpForRole(self, user, role):
        '''
        Ensure that regular users cannot login
        '''
        logger.debug("Running setUpForRole")
        if role == 'coldfront_user':
            user.is_active = False
            user.save()
