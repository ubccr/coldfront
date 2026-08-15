# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django.urls import include, path

from coldfront.registry import get_model_urls

from . import views

app_name = "core"
urlpatterns = [
    path("saved-filters/", include(get_model_urls("core", "savedfilter", detail=False))),
    path("saved-filters/<int:pk>/", include(get_model_urls("core", "savedfilter"))),
    path("table-configs/", include(get_model_urls("core", "tableconfig", detail=False))),
    path("table-configs/<int:pk>/", include(get_model_urls("core", "tableconfig"))),
    path("tags/", include(get_model_urls("core", "tag", detail=False))),
    path("tags/<int:pk>/", include(get_model_urls("core", "tag"))),
    path("changelog/", include(get_model_urls("core", "objectchange", detail=False))),
    path("changelog/<int:pk>/", include(get_model_urls("core", "objectchange"))),
    path("custom-field-choices/", include(get_model_urls("core", "customfieldchoiceset", detail=False))),
    path("custom-field-choices/<int:pk>/", include(get_model_urls("core", "customfieldchoiceset"))),
    path("custom-fields/", include(get_model_urls("core", "customfield", detail=False))),
    path("custom-fields/<int:pk>/", include(get_model_urls("core", "customfield"))),
    path("comment-entries/", include(get_model_urls("core", "commententry", detail=False))),
    path("comment-entries/<int:pk>/", include(get_model_urls("core", "commententry"))),
    path("jobs/", include(get_model_urls("core", "job", detail=False))),
    path("jobs/<int:pk>/", include(get_model_urls("core", "job"))),
    path("custom-links/", include(get_model_urls("core", "customlink", detail=False))),
    path("custom-links/<int:pk>/", include(get_model_urls("core", "customlink"))),
    path("plugins/", views.PluginListView.as_view(), name="plugin_list"),
    path("plugins/<str:name>/", views.PluginView.as_view(), name="plugin"),
    # Admin notification sending
    path("notifications/send/", views.AdminNotificationSendView.as_view(), name="notification_send"),
    # Markdown
    path("render/markdown/", views.RenderMarkdownView.as_view(), name="render_markdown"),
]
