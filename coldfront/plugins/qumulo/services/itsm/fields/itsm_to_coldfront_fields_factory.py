import os, yaml

from dotenv import load_dotenv

from coldfront.plugins.qumulo.services.itsm.fields.field import Field

load_dotenv(override=True)


ITSM_TO_COLDFRONT_MAP_PATH = os.environ.get("ITSM_TO_COLDFRONT_MAP_PATH") or (
    "coldfront/plugins/qumulo/static/migration_mappings/itsm_to_coldfront_map.yaml"
)

with open(ITSM_TO_COLDFRONT_MAP_PATH, "r") as file:
    itsm_to_coldfront_map = yaml.safe_load(file)
    field_map = itsm_to_coldfront_map["itsm_to_coldfront_map"]
    field_items = {key: value for key, value in field_map.items() if value is not None}
    itsm_attributes = field_items.keys()


class ItsmToColdfrontFieldsFactory:

    @staticmethod
    def get_fields(itsm_allocation) -> list:
        fields = []
        for item in field_items.values():
            itsm_value_field = item["itsm_value"]
            for coldfront_definitions in item["coldfront"]:
                value_attribute = itsm_allocation.get(itsm_value_field["attribute"])
                fields.append(
                    Field(coldfront_definitions, itsm_value_field, value_attribute)
                )
        return fields
