# -*- coding: utf-8 -*-

'''
Views
'''
from django.shortcuts import render

def unauthorized(request):
    '''
    Show product usages for which there is no authorized expense code
    '''
    return render(request, 'plugins/ifx/unauthorized.html')