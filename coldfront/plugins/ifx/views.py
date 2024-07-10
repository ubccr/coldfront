# -*- coding: utf-8 -*-

'''
Views
'''
import logging
import json
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from ifxreport.views import run_report as ifxreport_run_report
from ifxbilling import models as ifxbilling_models
from coldfront.plugins.ifx.calculator import NewColdfrontBillingCalculator

logger = logging.getLogger(__name__)

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
    # pylint: disable=broad-exception-raised
    raise Exception('Only POST allowed')

@login_required
@api_view(['POST',])
def calculate_billing_month(request, year, month):
    '''
    Calculate billing month view
    '''
    recalculate = False
    try:
        data = json.loads(request.body.decode('utf-8'))
        if data and 'recalculate' in data:
            recalculate = data['recalculate']
    except json.JSONDecodeError as e:
        logger.exception(e)
        return Response(data={'error': 'Cannot parse request body'}, status=status.HTTP_400_BAD_REQUEST)

    logger.debug('Calculating billing records for month %d of year %d, with recalculate flag %s', month, year, str(recalculate))

    try:
        if recalculate:
            ifxbilling_models.BillingRecord.objects.filter(year=year, month=month).delete()
        calculator = NewColdfrontBillingCalculator()
        resultinator = calculator.calculate_billing_month(year, month, recalculate=recalculate)
        successes = 0
        errors = []
        # pylint: disable=unused-variable
        for org, result in resultinator.results.items():
            if result.get('successes'):
                successes += len(result['successes'])
            if result.get('errors'):
                errors.extend(result['errors'])
        return Response(data={ 'successes': successes, 'errors': errors }, status=status.HTTP_200_OK)
    # pylint: disable=broad-exception-caught
    except Exception as e:
        logger.exception(e)
        return Response(data={ 'error': f'Billing calculation failed {e}' }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)