# SPDX-FileCopyrightText: (C) DigitalOcean, LLC
# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from rest_framework import serializers

from .features import ColdFrontModelSerializer

__all__ = (
    "NestedGroupModelSerializer",
    "OrganizationalModelSerializer",
    "PrimaryModelSerializer",
)


class PrimaryModelSerializer(ColdFrontModelSerializer):
    """
    Base serializer class for models inheriting from PrimaryModel.
    """

    pass


class NestedGroupModelSerializer(ColdFrontModelSerializer):
    """
    Base serializer class for models inheriting from NestedGroupModel.
    """

    _depth = serializers.IntegerField(source="level", read_only=True)


class OrganizationalModelSerializer(ColdFrontModelSerializer):
    """
    Base serializer class for models inheriting from OrganizationalModel.
    """

    pass
