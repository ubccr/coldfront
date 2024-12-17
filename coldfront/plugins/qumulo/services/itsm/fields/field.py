from typing import Any
import coldfront.plugins.qumulo.services.itsm.fields.transformers as value_transformers
import coldfront.plugins.qumulo.services.itsm.fields.validators as value_validators


class Field:
    def __init__(self, coldfront_definitions, itsm_value_field, value):
        self.coldfront_definitions = coldfront_definitions
        self._itsm_value_field = itsm_value_field
        self._coldfront_entity = coldfront_definitions["entity"]
        self._coldfront_attributes = coldfront_definitions["attributes"]
        self._value = value
        self._itsm_to_value = self.__get_value_definition()

    def __get_value_definition(self):
        entity = self.coldfront_definitions["entity"]
        if entity in ["allocation_attribute", "project_attribute"]:
            return next(
                value_item
                for value_item in self.coldfront_definitions["attributes"]
                if value_item["name"] == "value"
            )["value"]

        return self.coldfront_definitions["attributes"][0]["value"]

    @property
    def value(self) -> Any:
        return self.__transform_value()

    @property
    def entity(self) -> str:
        return self._coldfront_entity

    @property
    def attributes(self) -> str:
        return self._coldfront_attributes

    @property
    def entity_item(self) -> str:
        if self.entity == "allocation_form":
            return {self.attributes[0].get("name"): self.value}

        return None

    @property
    def itsm_attribute_name(self) -> str:
        return self._itsm_value_field["attribute"]

    def validate(self) -> list[str]:
        error_messages = []
        for attribute in self._coldfront_attributes:
            value = attribute["value"]
            if isinstance(value, dict):
                transforms = value["transforms"]

                to_be_validated = self._value or self.__get_default_value()
                if transforms is not None:
                    transforms_function = getattr(
                        value_transformers,
                        transforms,
                    )
                    to_be_validated = transforms_function(to_be_validated)

                for validator, conditions in value["validates"].items():
                    validator_function = getattr(
                        value_validators,
                        validator,
                    )
                    validation_message = validator_function(to_be_validated, conditions)
                    if validation_message:
                        error_messages.append(validation_message)

        return error_messages

    def __get_default_value(self) -> Any:
        return self._itsm_value_field.get("defaults_to")

    def is_valid(self) -> bool:
        return bool(self.validate())

    def __transform_value(self) -> Any:
        attribute_value = self._itsm_to_value
        transforms = attribute_value["transforms"]
        value = self._value or self.__get_default_value()
        if transforms is not None:
            transform_function = getattr(
                value_transformers,
                transforms,
            )
            value = transform_function(value)
        return value

    # Special getters
    def get_username(self) -> str:
        if self.entity != "user":
            return None

        if any(attribute["name"] == "username" for attribute in self.attributes):
            return self.value
        return None
