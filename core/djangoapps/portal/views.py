from django.conf import settings
from django.db.models import Q
from django.shortcuts import render

from core.djangoapps.project.models import Project
from core.djangoapps.subscription.models import Subscription
from extra.djangoapps.system_monitor.utils import get_system_monitor_context

from core.djangoapps.portal.utils import generate_publication_by_year_chart_data, generate_total_grants_by_agency_chart_data
from core.djangoapps.publication.models import Publication
from core.djangoapps.grant.models import Grant
from django.contrib.humanize.templatetags.humanize import intcomma

import operator

from django.db.models import Count, Sum
def home(request):

    context = {}
    if request.user.is_authenticated:
        template_name = 'portal/authorized_home.html'
        project_list = Project.objects.filter(
            (Q(pi=request.user) & Q(status__name__in=['New', 'Active', ])) |
            (Q(status__name__in=['New', 'Active', ]) &
             Q(projectuser__user=request.user) &
             Q(projectuser__status__name__in=['Active', 'Pending - Add', ]))
        ).distinct().order_by('-created')[:5]

        subscription_list = Subscription.objects.filter(
            Q(status__name__in=['Active', 'Approved', 'Denied', 'Expired', 'New', 'Pending', ]) &
            Q(project__status__name__in=['Active', 'New']) &
            Q(project__projectuser__user=request.user) &
            Q(project__projectuser__status__name__in=['Active', 'Pending - Add']) &
            Q(subscriptionuser__user=request.user) &
            Q(subscriptionuser__status__name__in=['Active', 'Pending - Add'])
        ).distinct().order_by('-created')[:5]
        context['project_list'] = project_list
        context['subscription_list'] = subscription_list
    else:
        template_name = 'portal/nonauthorized_home.html'

    context['EXTRA_APPS'] = settings.EXTRA_APPS

    if 'extra.djangoapps.system_monitor' in settings.EXTRA_APPS:
        context.update(get_system_monitor_context())

    return render(request, template_name, context)


def center_summary(request):
    context = {}


    # Publications Card
    publications_by_year = list(Publication.objects.filter(year__gte=1999).values('year').annotate(num_pub=Count('year')).order_by('-year'))

    publications_by_year = [(ele['year'], ele['num_pub']) for ele in publications_by_year]

    publication_by_year_bar_chart_data = generate_publication_by_year_chart_data(publications_by_year)
    context['publication_by_year_bar_chart_data'] = publication_by_year_bar_chart_data
    context['total_publications_count'] = Publication.objects.filter(year__gte=1999).count()

    # Grants Card
    total_grants_by_agency_sum = list(Grant.objects.values('funding_agency__name').annotate(total_amount=Sum('total_amount_awarded')))


    total_grants_by_agency_count = list(Grant.objects.values('funding_agency__name').annotate(count=Count('total_amount_awarded')))

    total_grants_by_agency_count = {ele['funding_agency__name']: ele['count'] for ele in total_grants_by_agency_count}

    total_grants_by_agency = [['{}: ${} ({})'.format(
        ele['funding_agency__name'],
        intcomma(int(ele['total_amount'])),
        total_grants_by_agency_count[ele['funding_agency__name']]
        ), ele['total_amount']] for ele in total_grants_by_agency_sum]

    total_grants_by_agency = sorted(total_grants_by_agency, key=operator.itemgetter(1), reverse=True)
    grants_agency_chart_data = generate_total_grants_by_agency_chart_data(total_grants_by_agency)
    context['grants_agency_chart_data'] = grants_agency_chart_data
    context['grants_total'] = intcomma(int(sum(list(Grant.objects.values_list('total_amount_awarded', flat=True)))))
    context['grants_total_pi_only'] = intcomma(int(sum(list(Grant.objects.filter(role='PI').values_list('total_amount_awarded', flat=True)))))
    context['grants_total_copi_only'] = intcomma(int(sum(list(Grant.objects.filter(role='CoPI').values_list('total_amount_awarded', flat=True)))))
    context['grants_total_sp_only'] = intcomma(int(sum(list(Grant.objects.filter(role='SP').values_list('total_amount_awarded', flat=True)))))

    return render(request, 'portal/center_summary.html', context)
