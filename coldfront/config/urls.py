"""
ColdFront URL Configuration
"""
from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView

import coldfront.core.portal.views as portal_views

admin.site.site_header = 'ColdFront Administration'
admin.site.site_title = 'ColdFront Administration'

urlpatterns = [
    path('admin/', admin.site.urls),
    path('robots.txt', TemplateView.as_view(template_name='robots.txt', content_type='text/plain'), name="robots"),
    path('', portal_views.home, name='home'),
    path('center-summary', portal_views.center_summary, name='center-summary'),
    path('allocation-summary', portal_views.allocation_summary, name='allocation-summary'),
    path('allocation-by-fos', portal_views.allocation_by_fos, name='allocation-by-fos'),
    path('user/', include('coldfront.core.user.urls')),
    path('project/', include('coldfront.core.project.urls')),
    path('allocation/', include('coldfront.core.allocation.urls')),
    path('jobs/', include('coldfront.core.statistics.urls')),
    # path('grant/', include('coldfront.core.grant.urls')),
    # path('publication/', include('coldfront.core.publication.urls')),
    # path('research-output/', include('coldfront.core.research_output.urls')),
    path('help', TemplateView.as_view(template_name='portal/help.html'), name='help'),
]


if 'coldfront.api' in settings.EXTRA_APPS:
    urlpatterns.append(path('api/', include('coldfront.api.urls')))

if 'coldfront.plugins.iquota' in settings.EXTRA_APPS:
    urlpatterns.append(path('iquota/', include('coldfront.plugins.iquota.urls')))

if 'mozilla_django_oidc' in settings.EXTRA_APPS:
    urlpatterns.append(path('oidc/', include('mozilla_django_oidc.urls')))

if 'django_su.backends.SuBackend' in settings.EXTRA_AUTHENTICATION_BACKENDS:
    urlpatterns.append(path('su/', include('django_su.urls')))

if ('allauth.account.auth_backends.AuthenticationBackend' in
        settings.EXTRA_AUTHENTICATION_BACKENDS):
    # Manually include only the desired URLs, rather than all of them.
    # urlpatterns.append(path('accounts/', include('allauth.urls')))
    prefixes_and_module_paths = [('accounts/', 'coldfront.core.account.urls')]
    if 'allauth.socialaccount' in settings.INSTALLED_APPS:
        prefixes_and_module_paths.extend([
            ('accounts/social/', 'coldfront.core.socialaccount.urls'),
            ('accounts/', 'allauth.socialaccount.providers.cilogon.urls'),
        ])
    for prefix, module_path in prefixes_and_module_paths:
        urlpatterns.append(path(prefix, include(module_path)))
