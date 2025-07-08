# SPDX-FileCopyrightText: (C) ColdFront Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

import django.dispatch

project_new = django.dispatch.Signal()
# providing_args=["project_obj"]

project_archive = django.dispatch.Signal()
# providing_args=["project_obj"]

project_update = django.dispatch.Signal()
# providing_args=["project_obj"]

project_activate_user = django.dispatch.Signal()
# providing_args=["project_user_pk"]

project_remove_user = django.dispatch.Signal()
# providing_args=["project_user_pk"]
