# -*- coding: utf-8 -*-

'''
Permissions classes for viewsets
'''

from rest_framework import permissions

def user_is_admin(user):
    '''
    Determine if user is an administrator
    '''
    return user.is_superuser or user.is_staff


class AdminPermissions(permissions.IsAuthenticated):
    '''
    User must be an admin
    '''

    def has_permission(self, request, view):
        '''
        Checking for Django is_staff
        '''
        return user_is_admin(request.user)


class FiineBillingRecordViewSetPermissions(permissions.IsAuthenticated):
    '''
    User must be an Admin or the person being updated
    '''

    def has_permission(self, request, view):
        '''
        Either admin or fiine user
        '''
        return request.user.username == 'fiine' or user_is_admin(request.user)
