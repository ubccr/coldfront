"""
Coldfront URL Configuration
"""
from django.conf import settings
from django.contrib import admin
from django.urls import include, path

import core.djangoapps.portal.views as portal_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('hijack/', include('hijack.urls', namespace='hijack')),
    path('', portal_views.home, name='home'),
    path('user/', include('common.djangoapps.user.urls')),
    path('project/', include('core.djangoapps.project.urls')),
    path('subscription/', include('core.djangoapps.subscription.urls')),
]


if 'extra.djangoapps.iquota' in settings.EXTRA_APPS:
    urlpatterns.append(path('iquota/', include('extra.djangoapps.iquota.urls')))


if 'extra.djangoapps.mokey_oidc' in settings.EXTRA_APPS:
    urlpatterns.append(path('mokey_oidc/', include('social_django.urls', namespace='social')))
