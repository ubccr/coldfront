# -*- coding: utf-8 -*-

'''
Views
'''
import logging
import json
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import connection
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.urls import reverse
from django_q.tasks import async_task
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.authentication import SessionAuthentication, BasicAuthentication, TokenAuthentication
from ifxreport.views import run_report as ifxreport_run_report
from ifxbilling import models as ifxbilling_models
from ifxbilling.calculator import getClassFromName
from ifxbilling.views import get_billing_record_list as ifxbilling_get_billing_record_list
from ifxbilling.fiine import update_user_accounts
from ifxbilling.calculator import get_rebalancer_class
from ifxmail.client import send
from ifxuser import models as ifxuser_models
from coldfront.plugins.ifx.calculator import NewColdfrontBillingCalculator
from coldfront.plugins.ifx.permissions import AdminPermissions
from coldfront.plugins.ifx.models import PreferredUsername

logger = logging.getLogger(__name__)

def get_preferred_user(ifxid):
    '''
    Get the IfxUser with the preferred username
    '''
    users = ifxuser_models.IfxUser.objects.filter(ifxid=ifxid)
    if not users:
        raise Exception(f'User cannot be found using ifxid {ifxid}')
    try:
        pu = PreferredUsername.objects.get(ifxid=ifxid)
        users = users.filter(username=pu.preferred_username)
    except PreferredUsername.DoesNotExist:
        pass
    except PreferredUsername.MultipleObjectsReturned:
        raise Exception(f'Multiple preferred usernames found for ifxid {ifxid}')
    if len(users) > 1:
        raise Exception(f'Multiple users found for ifxid {ifxid} and no preferred username is set')
    return users[0]


@login_required
def unauthorized(request):
    '''
    Show product usages for which there is no authorized expense code
    '''
    if not request.user.is_superuser:
        raise PermissionDenied
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
    if not request.user.is_superuser:
        raise PermissionDenied
    return render(request, 'plugins/ifx/reports.html')

@login_required
def run_report(request):
    '''
    Run the report
    '''
    if not request.user.is_superuser:
        raise PermissionDenied
    if request.method == 'POST':
        return ifxreport_run_report(request)
    # pylint: disable=broad-exception-raised
    raise Exception('Only POST allowed')

@login_required
def billing_month(request):
    '''
    Show billing month page
    '''
    if not request.user.is_superuser:
        raise PermissionDenied
    return render(request, 'plugins/ifx/calculate_billing_month.html')

@login_required
def billing_records(request):
    '''
    Show billing record list
    '''
    if not request.user.is_superuser:
        raise PermissionDenied
    delete_url = reverse('billing-record-detail', kwargs={'pk': 0})
    token = request.user.auth_token.key
    return render(request, 'plugins/ifx/billing_records.html', { 'delete_url': delete_url, 'auth_token': token })

@api_view(['GET',])
@authentication_classes([TokenAuthentication, SessionAuthentication, BasicAuthentication])
def get_billing_record_list(request):
    '''
    Get billing record list
    '''
    if not request.user.is_superuser:
        raise PermissionDenied
    return ifxbilling_get_billing_record_list(request._request)

@api_view(['POST',])
@permission_classes([AdminPermissions,])
def calculate_billing_month(request, invoice_prefix, year, month):
    '''
    Calculate billing month view
    '''
    logger.error('Calculating billing records for month %d of year %d', month, year)
    recalculate = False
    user_ifxorg = None
    try:
        data = request.data
        recalculate = data.get('recalculate') and data['recalculate'].lower() == 'true'
        if data and 'user_ifxorg' in data:
            user_ifxorg = data['user_ifxorg']
    except Exception as e:
        logger.exception(e)
        return Response(data={'error': 'Cannot parse request body'}, status=status.HTTP_400_BAD_REQUEST)

    logger.debug('Calculating billing records for month %d of year %d, with recalculate flag %s', month, year, str(recalculate))

    try:
        organizations = ifxuser_models.Organization.objects.filter(org_tree='Harvard')
        if user_ifxorg:
            organizations = [ifxuser_models.Organization.objects.get(ifxorg=user_ifxorg)]

        if recalculate:
            for br in ifxbilling_models.BillingRecord.objects.filter(year=year, month=month):
                br.delete()
            ifxbilling_models.ProductUsageProcessing.objects.filter(product_usage__year=year, product_usage__month=month).delete()
        calculator = NewColdfrontBillingCalculator()
        resultinator = calculator.calculate_billing_month(year, month, organizations=organizations, recalculate=recalculate)
        successes = 0
        errors = []
        for org, result in resultinator.results.items():
            if len(result[0]):
                successes += len(result[0])
        errors = [v[0] for v in resultinator.get_other_errors_by_organization().values()]

        return Response(data={ 'successes': successes, 'errors': errors }, status=status.HTTP_200_OK)
        return Response('OK', status=status.HTTP_200_OK)
    # pylint: disable=broad-exception-caught
    except Exception as e:
        logger.exception(e)
        return Response(data={ 'error': f'Billing calculation failed {e}' }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@login_required
@api_view(['GET',])
@permission_classes([AdminPermissions,])
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

@login_required
@api_view(('POST',))
@permission_classes([AdminPermissions,])
def send_billing_record_review_notification(request, year, month):
    '''
    Send billing record notification emails to organization contacts
    '''
    ifxorg_slugs = []
    test = []
    try:
        data = request.data
        if 'ifxorg_slugs' in data:
            ifxorg_slugs = data['ifxorg_slugs']
        if 'test' in data:
            test = data['test']
    except json.JSONDecodeError as e:
        logger.exception(e)
        return Response(data={'error': 'Cannot parse request body'}, status=status.HTTP_400_BAD_REQUEST)
    logger.info('Summarizing billing records for month %d of year %d, with ifxorg_slugs %s', month, year, ifxorg_slugs)

    facility = ifxbilling_models.Facility.objects.first()
    organizations = []
    if ifxorg_slugs:
        for ifxorg_slug in ifxorg_slugs:
            try:
                organizations.append(ifxuser_models.Organization.objects.get(slug=ifxorg_slug))
            except ifxuser_models.Organization.DoesNotExist:
                return Response(data={
                    'error': f'Organization with ifxorg number {ifxorg_slug} cannot be found'
                }, status=status.HTTP_400_BAD_REQUEST)
    logger.debug(f'Processing organizations {organizations}')
    try:
        breg_class_name = 'ifxbilling.notification.BillingRecordEmailGenerator'
        if hasattr(settings, 'BILLING_RECORD_EMAIL_GENERATOR_CLASS') and settings.BILLING_RECORD_EMAIL_GENERATOR_CLASS:
            app_name = settings.IFX_APP['name']
            breg_class_name = f'{app_name}.{settings.BILLING_RECORD_EMAIL_GENERATOR_CLASS}'
        breg_class = getClassFromName(breg_class_name)
        gen = breg_class(year, month, facility, test)
        successes, errors, nobrs = gen.send_billing_record_emails(organizations)
        logger.info(f'Billing record email successes: {", ".join(sorted([s.name for s in successes]))}')
        logger.info(f'Orgs with no billing records for {month}/{year}: {", ".join(sorted([n.name for n in nobrs]))}')
        for org_name, error_messages in errors.items():
            logger.error(f'Email errors for {org_name}: {", ".join(error_messages)} ')
        return Response(
            data={
                'successes': sorted([s.name for s in successes]),
                'errors': errors,
                'nobrs': sorted([n.name for n in nobrs if n.org_tree == 'Harvard'])
            },
            status=status.HTTP_200_OK
        )
    # pylint: disable=broad-except
    except Exception as e:
        logger.exception(e)
        return Response(data={ 'error': f'Billing record summary failed {str(e)}' }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

def update_user_accounts_and_notify(user_queryset, email):
    '''
    Update user accounts and notify the user by sending an email with ifxmail.client send()
    '''
    successes = 0
    errors = []

    for user in user_queryset:
        try:
            update_user_accounts(user)
            successes += 1
        except Exception as e:
            logger.exception(e)
            errors.append(f'Error updating {user}: {e}')


    fromstr = 'rchelp@rc.fas.harvard.edu'
    tostr = email
    message = f'{successes} user accounts updated successfully.'
    if errors:
        errorstr = '\n'.join(errors)
        message += f'Errors: {errorstr}'
    subject = "Update of user accounts"

    try:
        send(
            to=tostr,
            fromaddr=fromstr,
            message=message,
            subject=subject
        )
    except Exception as e:
        logger.exception(e)
        raise Exception(f'Error sending email to {tostr} from {fromstr} with message {message} and subject {subject}: {e}.') from e
    print('User accounts updated and email sent to %s', tostr)


@api_view(('POST',))
def update_user_accounts_view(request):
    '''
    Take a list of ifxids and update data from fiine.  Body should be of the form:
    {
        'ifxids': [
            'IFXID0001',
            'IFXID0002',
        ]
    }
    If no data is specified, all accounts will be updated
    '''
    logger.error('Updating user accounts in view')
    data = request.data

    if not data.keys():
        queryset = get_user_model().objects.filter(ifxid__isnull=False)
    else:
        queryset = get_user_model().objects.filter(ifxid__in=data['ifxids'])

    async_task(
        'coldfront.plugins.ifx.views.update_user_accounts_and_notify',
        queryset,
        request.user.email
    )

    return Response('OK')

@login_required
def lab_billing_summary(request):
    '''
    Show lab billing summary
    '''
    if not request.user.is_superuser:
        raise PermissionDenied
    token = request.user.auth_token.key
    return render(request, 'plugins/ifx/lab_billing_summary.html', { 'auth_token': token })


@api_view(('POST', ))
def rebalance(request):
    '''
    Rebalance the billing records for the given facility, user, year, and month.

    *** This is a copy of the ifxbilling view modified to handle preferred usernames ***
    '''
    try:
        data = json.loads(request.body.decode('utf-8'))
    except json.JSONDecodeError as e:
        logger.exception(e)
        return Response(data={'error': 'Cannot parse request body'}, status=status.HTTP_400_BAD_REQUEST)

    invoice_prefix = data.get('invoice_prefix', None)
    ifxid = data.get('ifxid', None)
    year = data.get('year', None)
    month = data.get('month', None)
    account_data = data.get('account_data', None)
    requestor_ifxid = data.get('requestor_ifxid', None)

    if not invoice_prefix:
        return Response(data={ 'error': 'invoice_prefix is required' }, status=status.HTTP_400_BAD_REQUEST)
    if not ifxid:
        return Response(data={ 'error': 'ifxid is required' }, status=status.HTTP_400_BAD_REQUEST)
    if not requestor_ifxid:
        return Response(data={ 'error': 'requestor_ifxid is required' }, status=status.HTTP_400_BAD_REQUEST)
    try:
        year = int(year)
    except ValueError:
        return Response(data={ 'error': 'year must be an integer' }, status=status.HTTP_400_BAD_REQUEST)
    try:
        month = int(month)
    except ValueError:
        return Response(data={ 'error': 'month must be an integer' }, status=status.HTTP_400_BAD_REQUEST)


    try:
        facility = ifxbilling_models.Facility.objects.get(invoice_prefix=invoice_prefix)
    except ifxbilling_models.Facility.DoesNotExist:
        return Response(data={ 'error': f'Facility cannot be found using invoice_prefix {invoice_prefix}' }, status=status.HTTP_400_BAD_REQUEST)

    try:
        user = get_preferred_user(ifxid)
    except Exception as e:
        return Response(data={ 'error': f'Error getting user with ifxid {ifxid}: {e}' }, status=status.HTTP_400_BAD_REQUEST)

    try:
        requestor = get_preferred_user(requestor_ifxid)
    except Exception as e:
        return Response(data={ 'error': f'Error getting requestor with ifxid {requestor_ifxid}: {e}' }, status=status.HTTP_400_BAD_REQUEST)


    auth_token_str = request.META.get('HTTP_AUTHORIZATION')
    rebalancer = get_rebalancer_class()(year, month, facility, auth_token_str, requestor)
    try:
        rebalancer.rebalance_user_billing_month(user, account_data)
        result = f'Rebalance of accounts for {user.full_name} for billing month {month}/{year} was successful.'
        rebalancer.send_result_notification(result)
        return Response(data={ 'success':  result })
    except Exception as e:
        logger.exception(e)
        result = f'Rebalance of accounts for {user.full_name} for billing month {month}/{year} failed: {e}'
        rebalancer.send_result_notification(result)
        return Response(data={ 'error': f'Rebalance failed {e}' }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(('GET',))
def user_account_list(request):
    '''
    Get a list of all usernames and the authorizations to which they are mapped
    '''
    results = []
    sql = '''
        select
            u.ifxid,
            u.full_name,
            u.username,
            ua.is_valid,
            '100' as percent,
            a.code,
            a.valid_from,
            a.expiration_date,
            o.name as organization,
            '' as product
        from
            ifxuser u
            inner join user_account ua on u.id = ua.user_id
            inner join account a on a.id = ua.account_id
            inner join nanites_organization o on o.id = a.organization_id
        where
            ua.is_valid = 1
        union
        select
            u.ifxid,
            u.full_name,
            u.username,
            upa.is_valid,
            upa.percent,
            a.code,
            a.valid_from,
            a.expiration_date,
            o.name as organization,
            p.product_name as product
        from
            ifxuser u
            inner join user_product_account upa on u.id = upa.user_id
            inner join account a on a.id = upa.account_id
            inner join nanites_organization o on o.id = a.organization_id
            inner join product p on p.id = upa.product_id
        where
            upa.is_valid = 1
    '''
    try:
        cursor = connection.cursor()
        cursor.execute(sql)

        desc = cursor.description

        for row in cursor.fetchall():
            # Make a dictionary labeled by column name
            results.append(dict(zip([col[0] for col in desc], row)))

    # pylint: disable=broad-except
    except Exception as e:
        logger.exception(e)
        return Response(
            f'Error getting user account list {e}',
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    return Response(
        data=results
    )
