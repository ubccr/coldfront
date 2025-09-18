# SPDX-FileCopyrightText: (C) ColdFront Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from django.urls import path

import coldfront.core.tag.views as tag_views

# TODO: add pattern for editing
urlpatterns = [
    path("<str:app_label>/<str:model_name>/<int:pk>/edit", tag_views.TagsEditView.as_view(), name="tags-edit"),
]
