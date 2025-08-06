# SPDX-FileCopyrightText: (C) ColdFront Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
ColdFront URL Configuration
"""

from django.conf import settings
from django.contrib import admin
from django.core import serializers
from django.http import HttpResponse
from django.urls import include, path
from django.views.generic import TemplateView

import coldfront.core.portal.views as portal_views

admin.site.site_header = "ColdFront Administration"
admin.site.site_title = "ColdFront Administration"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("robots.txt", TemplateView.as_view(template_name="robots.txt", content_type="text/plain"), name="robots"),
    path("", portal_views.home, name="home"),
    path("center-summary", portal_views.center_summary, name="center-summary"),
    path("allocation-summary", portal_views.allocation_summary, name="allocation-summary"),
    path("allocation-by-fos", portal_views.allocation_by_fos, name="allocation-by-fos"),
    path("user/", include("coldfront.core.user.urls")),
    path("project/", include("coldfront.core.project.urls")),
    path("allocation/", include("coldfront.core.allocation.urls")),
    path("resource/", include("coldfront.core.resource.urls")),
]

if settings.GRANT_ENABLE:
    urlpatterns.append(path("grant/", include("coldfront.core.grant.urls")))

if settings.PUBLICATION_ENABLE:
    urlpatterns.append(path("publication/", include("coldfront.core.publication.urls")))

if settings.RESEARCH_OUTPUT_ENABLE:
    urlpatterns.append(path("research-output/", include("coldfront.core.research_output.urls")))

if "coldfront.plugins.api" in settings.INSTALLED_APPS:
    urlpatterns.append(path("api/", include("coldfront.plugins.api.urls")))

if "coldfront.plugins.iquota" in settings.INSTALLED_APPS:
    urlpatterns.append(path("iquota/", include("coldfront.plugins.iquota.urls")))

if "mozilla_django_oidc" in settings.INSTALLED_APPS:
    urlpatterns.append(path("oidc/", include("mozilla_django_oidc.urls")))

if "django_su.backends.SuBackend" in settings.AUTHENTICATION_BACKENDS:
    urlpatterns.append(path("su/", include("django_su.urls")))


def export_as_json(modeladmin, request, queryset):
    response = HttpResponse(content_type="application/json")
    serializers.serialize("json", queryset, stream=response)
    return response


admin.site.add_action(export_as_json, "export_as_json")
