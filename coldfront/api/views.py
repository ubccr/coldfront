# SPDX-FileCopyrightText: (C) DigitalOcean, LLC
# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

import platform

from django import __version__ as DJANGO_VERSION
from django.conf import settings
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.views import APIView

from coldfront.plugins.utils import get_installed_plugins
from coldfront.users.api.serializers import UserSerializer


class APIRootView(APIView):
    """
    This is the root of ColdFront's REST API. API endpoints are arranged by app and model name; e.g. `/api/ras/projects/`.
    """

    _ignore_model_permissions = True

    def get_view_name(self):
        return "API Root"

    @extend_schema(exclude=True)
    def get(self, request, format=None):

        return Response(
            {
                "status": reverse("api-status", request=request, format=format),
                "users": reverse("users-api:api-root", request=request, format=format),
                "tenancy": reverse("tenancy-api:api-root", request=request, format=format),
                "core": reverse("core-api:api-root", request=request, format=format),
                "ras": reverse("ras-api:api-root", request=request, format=format),
                "ris": reverse("ris-api:api-root", request=request, format=format),
                "slurm": reverse("slurm-api:api-root", request=request, format=format),
                "storage": reverse("storage-api:api-root", request=request, format=format),
                "plugins": reverse("plugins-api:api-root", request=request, format=format),
            }
        )


class StatusView(APIView):
    """
    A lightweight read-only endpoint for conveying ColdFront's current operational status.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: OpenApiTypes.OBJECT})
    def get(self, request):
        return Response(
            {
                "django-version": DJANGO_VERSION,
                "coldfront-version": settings.VERSION,
                "plugins": get_installed_plugins(),
                "python-version": platform.python_version(),
            }
        )


class AuthenticationCheckView(APIView):
    """
    Return the user making the request, if authenticated successfully.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: OpenApiTypes.OBJECT})
    def get(self, request):
        serializer = UserSerializer(request.user, context={"request": request})
        return Response(serializer.data)
