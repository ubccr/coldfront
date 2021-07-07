# -*- coding: utf-8 -*-

'''
Permissions classes for viewsets
'''

from rest_framework import permissions



class FiineBillingRecordViewSetPermissions(permissions.IsAuthenticated):
    '''
    User must be an Admin or the person being updated
    '''
    def user_is_admin(self, user):
        '''
        Determine if user is an administrator
        '''
        return user.is_staff

    def has_permission(self, request, view):
        '''
        Either admin or fiine user
        '''
        return request.user.username == 'fiine' or self.user_is_admin(request.user)
