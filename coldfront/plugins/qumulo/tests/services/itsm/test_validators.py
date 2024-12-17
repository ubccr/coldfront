from django.test import TestCase

from coldfront.core.allocation.models import AllocationAttribute
from coldfront.core.test_helpers.factories import (
    AllocationAttributeFactory,
    AllocationAttributeTypeFactory,
)

from coldfront.plugins.qumulo.services.itsm.fields.validators import (
    exclusion,
    inclusion,
    length,
    numericallity,
    presence,
    validate_ticket,
    validate_json,
    uniqueness,
)


"""
python manage.py test coldfront.plugins.qumulo.tests.services.itsm.test_validators
"""


class TestValidators(TestCase):

    def setUp(self) -> None:
        return super().setUp()

    def test_validate_json(self):
        wellformed = """
        {"afm_cache_enable":true,"dir_projects":{"brc_regulome":{"ro":null,"rw":["mgi-svc-bga-admin","mgi-svc-bga-run"]},"bga1641":{"ro":null,"rw":["mgi-svc-bga-admin","mgi-svc-bga-run","jwalker"]}},"_jenkins":"https://systems-ci.gsc.wustl.edu/job/storage1_allocation/2483"}
        """
        self.assertIsNone(validate_json(wellformed))

        empty = "{}"
        self.assertIsNone(validate_json(empty))

        malformed = """
        {"afm_cache_enable":bad}
        """
        self.assertEqual(validate_json(malformed), "is not a valid JSON")

        conditions = {"allow_blank": True}
        blank = ""
        self.assertIsNone(validate_json(blank, conditions))
        self.assertIsNone(validate_json(None, conditions))

    def test_validate_ticket(self):
        self.assertIsNone(validate_ticket("ITSD-2222"))
        self.assertIsNone(validate_ticket("itsd-2222"))
        self.assertIsNone(validate_ticket("2222"))
        self.assertIsNone(validate_ticket(2222))

        validate = False
        self.assertIsNone(validate_ticket("", validate))

        self.assertEqual(
            validate_ticket("ITSD"), "ITSD is not in the format ITSD-12345 or 12345"
        )
        self.assertEqual(
            validate_ticket("ITSD2222"),
            "ITSD2222 is not in the format ITSD-12345 or 12345",
        )

    def test_numericallity(self) -> None:
        conditions = {
            "only_integer": True,
            "greater_than": 0,
            "less_than_or_equal_to": 2000,
        }
        # Truthy conditions
        self.assertIsNone(numericallity(200, conditions))
        self.assertIsNone(numericallity(1, conditions))
        self.assertIsNone(numericallity(2000, conditions))
        # Falsy conditions
        self.assertEqual(numericallity(-1, conditions), "must be greater than 0")
        self.assertEqual(numericallity(1.2, conditions), "1.2 is not an integer")
        self.assertEqual(numericallity(None, conditions), "None is not a number")
        self.assertEqual(numericallity(0, conditions), "must be greater than 0")
        self.assertEqual(
            numericallity(2001, conditions), "must be less than or equals to 2000"
        )

    def test_presence(self):
        # Truthy when presense is required
        value = "something"
        self.assertIsNone(presence(value, True))
        value = 10
        self.assertIsNone(presence(value, True))
        value = ["monthly"]
        self.assertIsNone(presence(value, True))

        # Falsy when presense is required
        value = ""
        self.assertEqual(presence(value, True), "must not be blank")
        value = None
        self.assertEqual(presence(value, True), "must be specified")

        # when presence is not required (optional)
        value = ""
        self.assertIsNone(presence(value, False), "must be specified")
        value = None
        self.assertIsNone(presence(value, False), "must be specified")

    def test_length(self):
        conditions = {"allow_blank": True, "maximum": 128}
        value = ""
        self.assertIsNone(length(value, conditions))
        value = None
        self.assertIsNone(length(value, conditions))
        value = "0123456789" * 12  # 120 chars
        self.assertIsNone(length(value, conditions))
        value = "0123456789" * 13  # 130 chars
        self.assertEqual(
            length(value, conditions), f"exceeds the limit of 128: {value}"
        )

        conditions = {"maximum": 128}
        value = ""
        self.assertEqual(length(value, conditions), "must not be blank")
        value = None
        self.assertEqual(length(value, conditions), "must not be blank")
        value = "0123456789" * 12
        self.assertIsNone(length(value, conditions))
        value = "0123456789" * 13
        self.assertEqual(
            length(value, conditions), f"exceeds the limit of 128: {value}"
        )

    def test_exclusion(self):
        exclude = "emails"
        self.assertIsNone(exclusion("wustl.key", exclude))
        an_email = "wustl.key@wustl.edu"
        error_message = f"constains an email and should only contain valid WUSTL keys: value {an_email}"
        self.assertEqual(exclusion("wustl.key@wustl.edu", exclude), error_message)

    def test_inclusion(self):
        accepted_values = ["monthly", "yearly", "quarterly", "prepaid", "fiscal year"]
        self.assertIsNone(inclusion("quarterly", accepted_values))

        self.assertEqual(
            inclusion(None, accepted_values),
            "None is not amongst ['monthly', 'yearly', 'quarterly', 'prepaid', 'fiscal year']",
        )
        self.assertEqual(
            inclusion(True, accepted_values),
            "True is not amongst ['monthly', 'yearly', 'quarterly', 'prepaid', 'fiscal year']",
        )
        self.assertEqual(
            inclusion(1, accepted_values),
            "1 is not amongst ['monthly', 'yearly', 'quarterly', 'prepaid', 'fiscal year']",
        )
        self.assertEqual(
            inclusion("Rube Goldberg", accepted_values),
            "Rube Goldberg is not amongst ['monthly', 'yearly', 'quarterly', 'prepaid', 'fiscal year']",
        )

        accepted_values = [True, False, "0", "1", None]
        self.assertIsNone(inclusion("0", accepted_values))
        self.assertIsNone(inclusion("1", accepted_values))
        self.assertIsNone(inclusion(0, accepted_values))
        self.assertIsNone(inclusion(1, accepted_values))
        self.assertIsNone(inclusion(False, accepted_values))
        self.assertIsNone(inclusion(True, accepted_values))
        self.assertIsNone(inclusion(None, accepted_values))

        self.assertEqual(
            inclusion(2, accepted_values),
            "2 is not amongst [True, False, '0', '1', None]",
        )
        self.assertEqual(
            inclusion("2", accepted_values),
            "2 is not amongst [True, False, '0', '1', None]",
        )

        accepted_values = ["smb", "nfs"]
        self.assertIsNone(inclusion("smb", accepted_values))
        self.assertIsNone(inclusion(["smb"], accepted_values))
        self.assertEqual(
            inclusion(["smb", "exoteric_protocol"], accepted_values),
            "['smb', 'exoteric_protocol'] is not amongst ['smb', 'nfs']",
        )

    def test_ad_record_exist(self):
        # TODO how?
        pass

    def test_uniqueness(self):
        allocation_attribute_type = AllocationAttributeTypeFactory(name="storage_name")
        value_to_be_compared = "i_exist"
        AllocationAttributeFactory(
            value=value_to_be_compared,
            allocation_attribute_type=allocation_attribute_type,
        )

        conditions = {
            "entity": "AllocationAttribute",
            "entity_attribute": "allocation_attribute_type__name",
            "attribute_name_value": "storage_name",
        }
        self.assertIsNone(uniqueness("i_do_not_exist", conditions))

        self.assertEqual(
            uniqueness(value_to_be_compared, conditions),
            f"{value_to_be_compared} is not unique for storage_name",
        )
