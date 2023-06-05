# -*- coding: utf-8 -*-

'''
Views
'''
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from ifxreport.views import run_report as ifxreport_run_report

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

@login_required
def report_runs(request):
    '''
    Show report runs page
    '''
    return render(request, 'plugins/ifx/reports.html')

@login_required
def run_report(request):
    '''
    Run the report
    '''
    if request.method == 'POST':
        return ifxreport_run_report(request)
    raise Exception('Only POST allowed')
