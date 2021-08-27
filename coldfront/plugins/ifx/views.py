# -*- coding: utf-8 -*-

'''
Views
'''
from django.shortcuts import render
from django.contrib.auth.decorators import login_required

@login_required
def unauthorized(request):
    '''
    Show product usages for which there is no authorized expense code
    '''
    return render(request, 'plugins/ifx/unauthorized.html')