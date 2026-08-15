# SPDX-FileCopyrightText: (C) DigitalOcean, LLC
# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django.contrib.contenttypes.models import ContentType

from coldfront.core.models import Tag
from coldfront.tenancy.models import Tenant
from coldfront.utils.testing import ViewTestCases


class TagTestCase(ViewTestCases.PrimaryObjectViewTestCase):
    model = Tag

    @classmethod
    def setUpTestData(cls):

        tenant_ct = ContentType.objects.get_for_model(Tenant)

        tags = (
            Tag(name="Tag 1", slug="tag-1"),
            Tag(name="Tag 2", slug="tag-2", weight=1),
            Tag(name="Tag 3", slug="tag-3", weight=32767),
        )
        Tag.objects.bulk_create(tags)

        cls.form_data = {
            "name": "Tag X",
            "slug": "tag-x",
            "color": "c0c0c0",
            "object_types": [tenant_ct.pk],
            "weight": 11,
        }

        cls.csv_data = (
            "name,slug,color,description,object_types,weight",
            "Tag 4,tag-4,ff0000,Fourth tag,ras.project,0",
            "Tag 5,tag-5,00ff00,Fifth tag,'ras.project,tenancy.tenant',1111",
            "Tag 6,tag-6,0000ff,Sixth tag,ras.allocation,0",
        )

        cls.csv_update_data = (
            "id,name,description",
            f"{tags[0].pk},Tag 7,Fourth tag7",
            f"{tags[1].pk},Tag 8,Fifth tag8",
            f"{tags[2].pk},Tag 9,Sixth tag9",
        )

        cls.bulk_edit_form_data = {
            "description": "Updated tag",
        }
