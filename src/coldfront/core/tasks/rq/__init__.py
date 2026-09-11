# SPDX-FileCopyrightText: Jake Howard and individual contributors
# SPDX-FileCopyrightText: (C) University at Buffalo (adapted for Django's built-in django.tasks)
# SPDX-License-Identifier: BSD-3-Clause

# Adopted from django-tasks-rq (BSD-3-Clause):
# https://github.com/RealOrangeOne/django-tasks-rq
# Adapted to bind to Django's built-in ``django.tasks`` module instead of the
# standalone ``django_tasks`` package.

from .backend import Job, RQBackend

__all__ = ["Job", "RQBackend"]
