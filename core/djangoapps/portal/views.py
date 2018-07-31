import json
from importlib import import_module

from django import forms
from django.conf import settings
from django.db.models import Q
from django.shortcuts import render
from django.utils.html import mark_safe
from django.views import View
from django.views.generic.base import TemplateView
from ldap3 import Connection, Server

from common.djangoapps.user.forms import UserSearchForm
from common.djangolibs.utils import import_from_settings
from core.djangoapps.project.models import Project
from core.djangoapps.subscription.models import Subscription
from extra.djangoapps.system_monitor.utils import get_system_monitor_context


def home(request):

    context = {}
    if request.user.is_authenticated:
        template_name = 'portal/authorized_home.html'
        project_list = Project.objects.filter(
            (Q(pi=request.user) & Q(status__name__in=['New', 'Active', ])) |
            (Q(status__name__in=['New', 'Active', ]) &
            Q(projectuser__user=request.user) &
            Q(projectuser__status__name__in=['Active', 'Pending Add', ]))
        ).order_by('-created').distinct()[:5]

        subscription_list = Subscription.objects.filter(
            Q(status__name__in=['Active', 'Pending', 'Approved', ]) &
            Q(subscriptionuser__user=request.user) &
            Q(subscriptionuser__status__name__in=['Active', 'Expired', 'Pending'])
        )
        context['project_list'] = project_list
        context['subscription_list'] = subscription_list
    else:
        template_name = 'portal/nonauthorized_home.html'

    context['EXTRA_APPS'] = settings.EXTRA_APPS

    if 'extra.djangoapps.system_monitor' in settings.EXTRA_APPS:
        context.update(get_system_monitor_context())

    return render(request, template_name, context)
