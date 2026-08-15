# SPDX-FileCopyrightText: (C) DigitalOcean, LLC
# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from rest_framework.viewsets import ModelViewSet

from tests.dummy_plugin.models import DummyModel

from .serializers import DummySerializer


class DummyViewSet(ModelViewSet):
    queryset = DummyModel.objects.all()
    serializer_class = DummySerializer
