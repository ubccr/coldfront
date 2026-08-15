# SPDX-FileCopyrightText: (C) DigitalOcean, LLC
# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

import logging

from django.db.models import Count
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.routers import APIRootView
from rest_framework.status import HTTP_201_CREATED
from rest_framework.views import APIView
from rest_framework.viewsets import ViewSet

from coldfront.api.viewsets import ColdFrontModelViewSet
from coldfront.users import filtersets
from coldfront.users.models import Group, ObjectPermission, Role, Token, User, UserConfig
from coldfront.users.querysets import RestrictedQuerySet
from coldfront.utils.data import deepmerge

from . import serializers


class UsersRootView(APIRootView):
    """
    Users API root view
    """

    def get_view_name(self):
        return "Users"


#
# Users and groups
#


class UserViewSet(ColdFrontModelViewSet):
    queryset = RestrictedQuerySet(model=User).order_by("username")
    serializer_class = serializers.UserSerializer
    filterset_class = filtersets.UserFilterSet


class GroupViewSet(ColdFrontModelViewSet):
    queryset = Group.objects.annotate(user_count=Count("user"))
    serializer_class = serializers.GroupSerializer
    filterset_class = filtersets.GroupFilterSet


#
# REST API tokens
#


class TokenViewSet(ColdFrontModelViewSet):
    queryset = Token.objects.all()
    serializer_class = serializers.TokenSerializer
    filterset_class = filtersets.TokenFilterSet


class TokenProvisionView(APIView):
    """
    Non-authenticated REST API endpoint via which a user may create a Token.
    """

    permission_classes = []

    @extend_schema(
        request=serializers.TokenProvisionSerializer,
        responses={
            201: serializers.TokenProvisionSerializer,
            401: OpenApiTypes.OBJECT,
        },
    )
    def post(self, request):
        serializer = serializers.TokenProvisionSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=HTTP_201_CREATED)

    def perform_create(self, serializer):
        model = serializer.Meta.model
        logger = logging.getLogger("coldfront.users.api.views.TokenProvisionView")
        logger.info(f"Creating new {model._meta.verbose_name}")
        serializer.save()


#
# User preferences
#


class UserConfigViewSet(ViewSet):
    """
    An API endpoint via which a user can update his or her own UserConfig data (but no one else's).
    """

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return UserConfig.objects.filter(user=self.request.user)

    @extend_schema(responses={200: OpenApiTypes.OBJECT})
    def list(self, request):
        """
        Return the UserConfig for the currently authenticated User.
        """
        userconfig = self.get_queryset().first()
        return Response(userconfig.data)

    @extend_schema(methods=["patch"], responses={201: OpenApiTypes.OBJECT})
    def patch(self, request):
        """
        Update the UserConfig for the currently authenticated User.
        """
        userconfig, _ = self.get_queryset().get_or_create(user=request.user)
        userconfig.data = deepmerge(userconfig.data, request.data)
        userconfig.save()
        return Response(userconfig.data)


#
# Roles
#


class RoleViewSet(ColdFrontModelViewSet):
    queryset = Role.objects.all()
    serializer_class = serializers.RoleSerializer
    filterset_class = filtersets.RoleFilterSet


#
# ObjectPermissions
#


class ObjectPermissionViewSet(ColdFrontModelViewSet):
    queryset = ObjectPermission.objects.all()
    serializer_class = serializers.ObjectPermissionSerializer
    filterset_class = filtersets.ObjectPermissionFilterSet
