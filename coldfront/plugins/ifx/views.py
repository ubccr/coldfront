# -*- coding: utf-8 -*-

'''
Views
'''
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils import timezone

@login_required
def unauthorized(request):
    '''
    Show product usages for which there is no authorized expense code
    '''
    year = timezone.now().year
    month = timezone.now().month
    years = list(range(2021, 2030))
    months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
    return render(request, 'plugins/ifx/unauthorized.html', {'months': months, 'years': years, 'year': year, 'month': month})
