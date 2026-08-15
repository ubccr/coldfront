# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django.test import TestCase

from coldfront.core.models import ObjectType
from coldfront.ras.models import Resource


class AllocatableResourceFeatureTest(TestCase):
    def test_resource_has_allocatable_resource_feature(self):
        """
        Verify that the Resource model is registered with the "allocatable_resource" feature.
        """
        self.assertTrue(ObjectType.has_feature(Resource, "allocatable_resource"))

    def test_resource_allocatable_resource_in_features_list(self):
        """
        Verify that "allocatable_resource" appears in the list of features for Resource.
        """
        features = ObjectType.get_model_features(Resource)
        self.assertIn("allocatable_resource", features)
