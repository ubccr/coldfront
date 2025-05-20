"""
ColdFront URL Configuration
"""
from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView

import coldfront.core.portal.views as portal_views

admin.site.site_header = 'RT Projects Administration'
admin.site.site_title = 'RT Projects Administration'

urlpatterns = [
    path('admin/', admin.site.urls),
    path('robots.txt', TemplateView.as_view(template_name='robots.txt', content_type='text/plain'), name="robots"),
    path('', portal_views.home, name='home'),
    path('center-summary', portal_views.center_summary, name='center-summary'),
    path('allocation-summary', portal_views.allocation_summary, name='allocation-summary'),
    path('allocation-by-fos', portal_views.allocation_by_fos, name='allocation-by-fos'),
    path('project-summary', portal_views.project_summary, name='project-summary'),
    path('user-summary', portal_views.user_summary, name='user-summary'),
    path('user/', include('coldfront.core.user.urls')),
    path('project/', include('coldfront.core.project.urls')),
    path('allocation/', include('coldfront.core.allocation.urls')),
    path('resource/', include('coldfront.core.resource.urls')),
]

if settings.GRANT_ENABLE:
    urlpatterns.append(path('grant/', include('coldfront.core.grant.urls')))

if settings.PUBLICATION_ENABLE:
    urlpatterns.append(path('publication/', include('coldfront.core.publication.urls')))

if settings.RESEARCH_OUTPUT_ENABLE:
    urlpatterns.append(path('research-output/', include('coldfront.core.research_output.urls')))

if 'coldfront.plugins.movable_allocations' in settings.INSTALLED_APPS:
    urlpatterns.append(path('movable_allocations/', include('coldfront.plugins.movable_allocations.urls')))

if 'coldfront_custom_resources' in settings.INSTALLED_APPS:
    urlpatterns.append(path('custom_resources/', include('coldfront_custom_resources.urls')))

if 'coldfront.plugins.announcements' in settings.INSTALLED_APPS:
    urlpatterns.append(path('announcements/', include('coldfront.plugins.announcements.urls')))

if 'coldfront.plugins.allocation_removal_requests' in settings.INSTALLED_APPS:
    urlpatterns.append(path('allocation_removal_requests/', include('coldfront.plugins.allocation_removal_requests.urls')))

if 'coldfront.plugins.pi_search' in settings.INSTALLED_APPS:
    urlpatterns.append(path('pi_search_function/', include('coldfront.plugins.pi_search.urls')))

if 'coldfront.plugins.customizable_forms' in settings.INSTALLED_APPS:
    urlpatterns.append(path('allocation/', include('coldfront.plugins.customizable_forms.urls')))

if 'coldfront.plugins.academic_analytics' in settings.INSTALLED_APPS:
    urlpatterns.append(path('academic-analytics/', include('coldfront.plugins.academic_analytics.urls')))

if 'coldfront.plugins.advanced_search' in settings.INSTALLED_APPS:
    urlpatterns.append(path('advanced_search/', include('coldfront.plugins.advanced_search.urls')))

if 'coldfront.plugins.ldap_user_info' in settings.INSTALLED_APPS:
    urlpatterns.append(path('ldap_user_info/', include('coldfront.plugins.ldap_user_info.urls')))

if 'coldfront.plugins.iquota' in settings.INSTALLED_APPS:
    urlpatterns.append(path('iquota/', include('coldfront.plugins.iquota.urls')))

if 'mozilla_django_oidc' in settings.INSTALLED_APPS:
    urlpatterns.append(path('oidc/', include('mozilla_django_oidc.urls')))

if 'django_su.backends.SuBackend' in settings.AUTHENTICATION_BACKENDS:
    urlpatterns.append(path('su/', include('django_su.urls')))
