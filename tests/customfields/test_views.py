# SPDX-FileCopyrightText: (C) DigitalOcean, LLC
# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from coldfront.core.choices import (
    CustomFieldFilterLogicChoices,
    CustomFieldTypeChoices,
    CustomFieldUIEditableChoices,
    CustomFieldUIVisibleChoices,
)
from coldfront.core.models import CustomField, CustomFieldChoiceSet, ObjectType
from coldfront.tenancy.models import Tenant
from coldfront.utils.testing import ViewTestCases


class CustomFieldChoiceSetTestCase(ViewTestCases.PrimaryObjectViewTestCase):
    model = CustomFieldChoiceSet

    @classmethod
    def setUpTestData(cls):

        choice_sets = (
            CustomFieldChoiceSet(name="Choice Set 1", choices=["A1:Choice 1", "A2:Choice 2", "A3:Choice 3"]),
            CustomFieldChoiceSet(name="Choice Set 2", choices=["B1:Choice 1", "B2:Choice 2", "B3:Choice 3"]),
            CustomFieldChoiceSet(name="Choice Set 3", choices=["C1:Choice 1", "C2:Choice 2", "C3:Choice 3"]),
            CustomFieldChoiceSet(name="Choice Set 4", choices=["D1:Choice 1", "D2:Choice 2", "D3:Choice 3"]),
        )
        CustomFieldChoiceSet.objects.bulk_create(choice_sets)

        cls.form_data = {
            "name": "Choice Set X",
            "choices": '["X1:Choice 1", "X2:Choice 2", "X3:Choice 3"]',
        }

        cls.csv_data = (
            "name,choices",
            'Choice Set 5,"D1,D2,D3"',
            'Choice Set 6,"E1,E2,E3"',
            'Choice Set 7,"F1,F2,F3"',
            'Choice Set 8,"F1:L1,F2:L2,F3:L3"',
        )

        cls.csv_update_data = (
            "id,choices",
            f'{choice_sets[0].pk},"A,B,C"',
            f'{choice_sets[1].pk},"A,B,C"',
            f'{choice_sets[2].pk},"A,B,C"',
            f'{choice_sets[3].pk},"A:L1,B:L2,C:L3"',
        )

        cls.bulk_edit_form_data = {
            "description": "New description",
        }


class CustomFieldTestCase(ViewTestCases.PrimaryObjectViewTestCase):
    model = CustomField

    @classmethod
    def setUpTestData(cls):

        tenant_type = ObjectType.objects.get_for_model(Tenant)
        CustomFieldChoiceSet.objects.create(
            name="Choice Set 1",
            choices=(
                "A:A",
                "B:B",
                "C:C",
            ),
        )

        custom_fields = (
            CustomField(name="field1", label="Field 1", type=CustomFieldTypeChoices.TYPE_TEXT),
            CustomField(name="field2", label="Field 2", type=CustomFieldTypeChoices.TYPE_TEXT),
            CustomField(name="field3", label="Field 3", type=CustomFieldTypeChoices.TYPE_TEXT),
        )
        for customfield in custom_fields:
            customfield.save()
            customfield.object_types.add(tenant_type)

        cls.form_data = {
            "name": "field_x",
            "label": "Field X",
            "type": "text",
            "object_types": [tenant_type.pk],
            "search_weight": 2000,
            "filter_logic": CustomFieldFilterLogicChoices.FILTER_EXACT,
            "default": None,
            "weight": 200,
            "required": True,
            "ui_visible": CustomFieldUIVisibleChoices.ALWAYS,
            "ui_editable": CustomFieldUIEditableChoices.YES,
        }

        cls.csv_data = (
            "name,label,type,object_types,related_object_type,weight,search_weight,filter_logic,choice_set,validation_minimum,validation_maximum,validation_regex,ui_visible,ui_editable",
            "field4,Field 4,text,ras.project,,100,1000,exact,,,,[a-z]{3},always,yes",
            "field5,Field 5,integer,ras.project,,100,2000,exact,,1,100,,always,yes",
            "field6,Field 6,select,ras.project,,100,3000,exact,Choice Set 1,,,,always,yes",
            "field7,Field 7,object,ras.project,ras.allocation,100,4000,exact,,,,,always,yes",
        )

        cls.csv_update_data = (
            "id,label",
            f"{custom_fields[0].pk},New label 1",
            f"{custom_fields[1].pk},New label 2",
            f"{custom_fields[2].pk},New label 3",
        )

        cls.bulk_edit_form_data = {
            "label": "Updated label",
        }
