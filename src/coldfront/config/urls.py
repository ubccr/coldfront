# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

"""
ColdFront URL Configuration
"""

import environ
import split_settings
from django.conf import settings
from django.contrib import admin
from django.core import serializers
from django.http import HttpResponse
from django.urls import include, path
from django.views.decorators.cache import cache_page
from django.views.generic import TemplateView
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

from coldfront.account.views import ColdFrontLoginView, HtmxLogoutView
from coldfront.api.views import APIRootView, AuthenticationCheckView, StatusView
from coldfront.config.env import ENV, PROJECT_ROOT
from coldfront.plugins.urls import plugin_api_patterns, plugin_patterns
from coldfront.views import HomeView, ObjectSelectorView

admin.site.site_header = "ColdFront Administration"
admin.site.site_title = "ColdFront Administration"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("robots.txt", TemplateView.as_view(template_name="robots.txt", content_type="text/plain"), name="robots"),
    # Base views
    path("", HomeView.as_view(), name="home"),
    # Login/logout
    path(
        "login",
        ColdFrontLoginView.as_view(),
        name="login",
    ),
    path("logout/", HtmxLogoutView.as_view(), name="logout"),
    path("oauth/", include("social_django.urls", namespace="social")),
    # User profile views
    # HTMX views
    path("htmx/object-selector/", ObjectSelectorView.as_view(), name="htmx_object_selector"),
    path("user/", include("coldfront.account.urls")),
    # ColdFront core apps
    path("users/", include("coldfront.users.urls")),
    path("core/", include("coldfront.core.urls")),
    path("tenancy/", include("coldfront.tenancy.urls")),
    path("ras/", include("coldfront.ras.urls")),
    path("slurm/", include("coldfront.slurm.urls")),
    path("storage/", include("coldfront.storage.urls")),
    path("ris/", include("coldfront.ris.urls")),
    path("billing/", include("coldfront.billing.urls")),
    # REST API
    path("api/", APIRootView.as_view(), name="api-root"),
    path("api/status/", StatusView.as_view(), name="api-status"),
    path("api/authentication-check/", AuthenticationCheckView.as_view(), name="api-authentication-check"),
    path("api/users/", include("coldfront.users.api.urls")),
    path("api/tenancy/", include("coldfront.tenancy.api.urls")),
    path("api/core/", include("coldfront.core.api.urls")),
    path("api/ras/", include("coldfront.ras.api.urls")),
    path("api/ris/", include("coldfront.ris.api.urls")),
    path("api/slurm/", include("coldfront.slurm.api.urls")),
    path("api/storage/", include("coldfront.storage.api.urls")),
    path("api/billing/", include("coldfront.billing.api.urls")),
    # REST API schema
    path(
        "api/schema/",
        cache_page(timeout=86400, key_prefix=f"api_schema_{settings.VERSION}")(SpectacularAPIView.as_view()),
        name="schema",
    ),
    path("api/schema/swagger-ui/", SpectacularSwaggerView.as_view(url_name="schema"), name="api_docs"),
    path("api/schema/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="api_redocs"),
    # Plugins
    path("plugins/", include((plugin_patterns, "plugins"))),
    path("api/plugins/", include((plugin_api_patterns, "plugins-api"))),
]

if "mozilla_django_oidc" in settings.INSTALLED_APPS:
    urlpatterns.append(path("oidc/", include("mozilla_django_oidc.urls")))


def export_as_json(modeladmin, request, queryset):
    response = HttpResponse(content_type="application/json")
    serializers.serialize("json", queryset, stream=response)
    return response


admin.site.add_action(export_as_json, "export_as_json")

# Local urls overrides
local_urls = [
    # Local urls relative to coldfront.config package
    "local_urls.py",
    # System wide urls for production deployments
    "/etc/coldfront/local_urls.py",
    # Local urls relative to coldfront project root
    PROJECT_ROOT("local_urls.py"),
]

if ENV.str("COLDFRONT_URLS", default="") != "":
    # Local urls from path specified via environment variable
    local_urls.append(environ.Path(ENV.str("COLDFRONT_URLS"))())

for lu in local_urls:
    split_settings.tools.include(split_settings.tools.optional(lu))
