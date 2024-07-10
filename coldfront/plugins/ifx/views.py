# -*- coding: utf-8 -*-

'''
Views
'''
import logging
import json
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db import connection
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
def billing_month(request):
    '''
    Show billing month page
    '''
    return render(request, 'plugins/ifx/calculate_billing_month.html')

@login_required
def billing_records(request):
    '''
    Show billing record list
    '''
    return render(request, 'plugins/ifx/billing_records.html')

@login_required
@api_view(['POST',])
def calculate_billing_month(request, year, month):
    '''
    Calculate billing month view
    '''
    logger.error('Calculating billing records for month %d of year %d', month, year)
    recalculate = False
    try:
        data = request.data
        logger.error('Request data: %s', data)
        recalculate = data.get('recalculate') and data['recalculate'].lower() == 'true'
    except Exception as e:
        logger.exception(e)
        return Response(data={'error': 'Cannot parse request body'}, status=status.HTTP_400_BAD_REQUEST)

    logger.debug('Calculating billing records for month %d of year %d, with recalculate flag %s', month, year, str(recalculate))

    try:
        if recalculate:
            ifxbilling_models.BillingRecord.objects.filter(year=year, month=month).delete()
        calculator = NewColdfrontBillingCalculator()
        calculator.calculate_billing_month(year, month, recalculate=recalculate)
        return Response('OK', status=status.HTTP_200_OK)
    # pylint: disable=broad-exception-caught
    except Exception as e:
        logger.exception(e)
        return Response(data={ 'error': f'Billing calculation failed {e}' }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@login_required
@api_view(['GET',])
def get_product_usages(request):
    '''
    Get product usages
    '''
    local_tz = timezone.get_current_timezone()

    year = request.GET.get('year', None)
    month = request.GET.get('month', None)
    errors_only = request.GET.get('errors_only', False)
    results = []
    sql = f'''
        select
            pu.id,
            pu.year,
            pu.month,
            pu.description,
            p.product_name,
            u.full_name,
            o.name as organization,
            CONVERT_TZ(pu.start_date, 'UTC', '{local_tz}') as start_date,
            CONVERT_TZ(pu.end_date, 'UTC', '{local_tz}') as end_date,
            pup.error_message,
            pup.resolved
        from
            product_usage pu
            inner join product p on p.id = pu.product_id
            inner join ifxuser u on u.id = pu.product_user_id
            inner join nanites_organization o on o.id = pu.organization_id
            left join product_usage_processing pup on pup.product_usage_id = pu.id
    '''
    where_clauses = []
    query_args = []
    if year:
        try:
            year = int(year)
        except ValueError:
            return Response('year must be an integer', status=status.HTTP_400_BAD_REQUEST)
        where_clauses.append('pu.year = %s')
        query_args.append(year)

    if month:
        try:
            month = int(month)
        except ValueError:
            return Response('month must be an integer', status=status.HTTP_400_BAD_REQUEST)
        where_clauses.append('pu.month = %s')
        query_args.append(month)

    if errors_only and errors_only.lower() == 'true':
        where_clauses.append('pup.resolved = 0' )

    if where_clauses:
        sql += ' where '
        sql += ' and '.join(where_clauses)

    sql += ' order by organization, full_name, product_name'

    try:
        cursor = connection.cursor()
        cursor.execute(sql, query_args)

        desc = cursor.description

        for row in cursor.fetchall():
            # Make a dictionary labeled by column name
            results.append(dict(zip([col[0] for col in desc], row)))

    # pylint: disable=broad-except
    except Exception as e:
        logger.exception(e)
        return Response(
            f'Error getting product usages {e}',
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    return Response(
        data=results
    )
