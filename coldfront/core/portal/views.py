import operator
from collections import Counter

from django.conf import settings
from django.contrib.humanize.templatetags.humanize import intcomma
from django.db.models import Count, Q, Sum
from django.shortcuts import render
from django.views.decorators.cache import cache_page

from coldfront.core.grant.models import Grant
from coldfront.core.portal.utils import (generate_publication_by_year_chart_data,
                                          generate_resources_chart_data,
                                          generate_subscriptions_chart_data,
                                          generate_total_grants_by_agency_chart_data)
from coldfront.core.project.models import Project
from coldfront.core.publication.models import Publication
from coldfront.core.subscription.models import Subscription, SubscriptionUser



def home(request):

    context = {}
    if request.user.is_authenticated:
        template_name = 'portal/authorized_home.html'
        project_list = Project.objects.filter(
            (Q(pi=request.user) & Q(status__name__in=['New', 'Active', ])) |
            (Q(status__name__in=['New', 'Active', ]) &
             Q(projectuser__user=request.user) &
             Q(projectuser__status__name__in=['Active', ]))
        ).distinct().order_by('-created')[:5]

        subscription_list = Subscription.objects.filter(
            Q(status__name__in=['Active', 'New', 'Renewal Requested', ]) &
            Q(project__status__name__in=['Active', 'New']) &
            Q(project__projectuser__user=request.user) &
            Q(project__projectuser__status__name__in=['Active', ]) &
            Q(subscriptionuser__user=request.user) &
            Q(subscriptionuser__status__name__in=['Active', ])
        ).distinct().order_by('-created')[:5]
        context['project_list'] = project_list
        context['subscription_list'] = subscription_list
    else:
        template_name = 'portal/nonauthorized_home.html'

    context['EXTRA_APPS'] = settings.EXTRA_APPS

    if 'coldfront.plugins.system_monitor' in settings.EXTRA_APPS:
        from coldfront.plugins.system_monitor.utils import get_system_monitor_context
        context.update(get_system_monitor_context())

    return render(request, template_name, context)


def center_summary(request):
    context = {}

    # Publications Card
    publications_by_year = list(Publication.objects.filter(year__gte=1999).values(
        'unique_id', 'year').distinct().values('year').annotate(num_pub=Count('year')).order_by('-year'))

    publications_by_year = [(ele['year'], ele['num_pub']) for ele in publications_by_year]

    publication_by_year_bar_chart_data = generate_publication_by_year_chart_data(publications_by_year)
    context['publication_by_year_bar_chart_data'] = publication_by_year_bar_chart_data
    context['total_publications_count'] = Publication.objects.filter(
        year__gte=1999).values('unique_id', 'year').distinct().count()

    # Grants Card
    total_grants_by_agency_sum = list(Grant.objects.values(
        'funding_agency__name').annotate(total_amount=Sum('total_amount_awarded')))

    total_grants_by_agency_count = list(Grant.objects.values(
        'funding_agency__name').annotate(count=Count('total_amount_awarded')))

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
    context['grants_total_pi_only'] = intcomma(
        int(sum(list(Grant.objects.filter(role='PI').values_list('total_amount_awarded', flat=True)))))
    context['grants_total_copi_only'] = intcomma(
        int(sum(list(Grant.objects.filter(role='CoPI').values_list('total_amount_awarded', flat=True)))))
    context['grants_total_sp_only'] = intcomma(
        int(sum(list(Grant.objects.filter(role='SP').values_list('total_amount_awarded', flat=True)))))

    return render(request, 'portal/center_summary.html', context)


@cache_page(60 * 15)
def subscription_by_fos(request):

    subscriptions_by_fos = Counter(list(Subscription.objects.filter(
        status__name='Active').values_list('project__field_of_science__description', flat=True)))

    user_subscriptions = SubscriptionUser.objects.filter(status__name='Active', subscription__status__name='Active')

    active_users_by_fos = Counter(list(user_subscriptions.values_list(
        'subscription__project__field_of_science__description', flat=True)))
    total_subscriptions_users = user_subscriptions.values('user').distinct().count()

    active_pi_count = Project.objects.filter(status__name__in=['Active', 'New']).values_list(
        'pi__username', flat=True).distinct().count()
    context = {}
    context['subscriptions_by_fos'] = dict(subscriptions_by_fos)
    context['active_users_by_fos'] = dict(active_users_by_fos)
    context['total_subscriptions_users'] = total_subscriptions_users
    context['active_pi_count'] = active_pi_count
    return render(request, 'portal/subscription_by_fos.html', context)


@cache_page(60 * 15)
def subscription_summary(request):

    subscription_resources = [
        s.get_parent_resource.parent_resource if s.get_parent_resource.parent_resource else s.get_parent_resource for s in Subscription.objects.filter(status__name='Active')]

    subscriptions_count_by_resource = dict(Counter(subscription_resources))

    subscription_count_by_resource_type = dict(Counter([ele.resource_type.name for ele in subscription_resources]))

    subscriptions_chart_data = generate_subscriptions_chart_data()
    resources_chart_data = generate_resources_chart_data(subscription_count_by_resource_type)

    context = {}
    context['subscriptions_chart_data'] = subscriptions_chart_data
    context['subscriptions_count_by_resource'] = subscriptions_count_by_resource
    context['resources_chart_data'] = resources_chart_data


    return render(request, 'portal/subscription_summary.html', context)
