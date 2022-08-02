from coldfront.core.utils.common import display_time_zone_date_to_utc_datetime


def job_query_filtering(job_list, data):
    if data.get('status'):
        job_list = job_list.filter(
            jobstatus__icontains=data.get('status'))

    if data.get('jobslurmid'):
        job_list = job_list.filter(
            jobslurmid__icontains=data.get('jobslurmid'))

    if data.get('project_name'):
        job_list = job_list.filter(
            accountid__name__icontains=data.get('project_name'))

    if data.get('username'):
        job_list = job_list.filter(
            userid__username__icontains=data.get('username'))

    if data.get('partition'):
        job_list = job_list.filter(
            partition__icontains=data.get('partition'))

    if data.get('amount'):
        if data.get('amount_modifier') == 'leq':
            job_list = job_list.filter(amount__lte=data.get('amount'))
        else:
            job_list = job_list.filter(amount__gte=data.get('amount'))

    if data.get('submitdate'):
        submit_modifier = data.get('submit_modifier')
        submit_date = display_time_zone_date_to_utc_datetime(
            data.get('submitdate'))

        if submit_modifier == 'Before':
            job_list = job_list.filter(submitdate__lt=submit_date)
        elif submit_modifier == 'On':
            job_list = job_list.filter(submitdate__year=submit_date.year,
                                       submitdate__month=submit_date.month,
                                       submitdate__day=submit_date.day)
        elif submit_modifier == 'After':
            job_list = job_list.filter(submitdate__gt=submit_date)

    if data.get('startdate'):
        start_modifier = data.get('start_modifier')
        start_date = display_time_zone_date_to_utc_datetime(
            data.get('startdate'))

        if start_modifier == 'Before':
            job_list = job_list.filter(startdate__lt=start_date)
        elif start_modifier == 'On':
            job_list = job_list.filter(startdate__year=start_date.year,
                                       startdate__month=start_date.month,
                                       startdate__day=start_date.day)
        elif start_modifier == 'After':
            job_list = job_list.filter(startdate__gt=start_date)

    if data.get('enddate'):
        end_modifier = data.get('end_modifier')
        end_date = display_time_zone_date_to_utc_datetime(data.get('enddate'))

        if end_modifier == 'Before':
            job_list = job_list.filter(enddate__lt=end_date)
        elif end_modifier == 'On':
            job_list = job_list.filter(enddate__year=end_date.year,
                                       enddate__month=end_date.month,
                                       enddate__day=end_date.day)
        elif end_modifier == 'After':
            job_list = job_list.filter(enddate__gt=end_date)

    return job_list
