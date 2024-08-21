"""
ColdFront URL Configuration
"""
from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView
from django.conf.urls.static import static

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
    path('grant/', include('coldfront.core.grant.urls')),
    path('publication/', include('coldfront.core.publication.urls')),
    path('research-output/', include('coldfront.core.research_output.urls')), 
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

if 'coldfront.plugins.academic_analytics' in settings.INSTALLED_APPS:
    urlpatterns.append(path('academic-analytics/', include('coldfront.plugins.academic_analytics.urls')))

if 'coldfront.plugins.advanced_search' in settings.INSTALLED_APPS:
    urlpatterns.append(path('advanced_search/', include('coldfront.plugins.advanced_search.urls')))

if 'coldfront.plugins.slate_project' in settings.INSTALLED_APPS:
    urlpatterns.append(path('slate_project/', include('coldfront.plugins.slate_project.urls')))

if 'coldfront.plugins.iquota' in settings.INSTALLED_APPS:
    urlpatterns.append(path('iquota/', include('coldfront.plugins.iquota.urls')))

if 'mozilla_django_oidc' in settings.INSTALLED_APPS:
    urlpatterns.append(path('oidc/', include('mozilla_django_oidc.urls')))

if 'django_su.backends.SuBackend' in settings.AUTHENTICATION_BACKENDS:
    urlpatterns.append(path('su/', include('django_su.urls')))
