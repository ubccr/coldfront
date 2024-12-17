import math, os
from typing import Optional


def fileset_name_to_storage_filesystem_path(fileset_name_or_alias) -> str:
    # In ITSM, fileset_names are mapped into name
    # Examples
    # bisiademuyiwa_active --> /storage2/fs1/bisiademuyiwa
    # gc6159 --> /storage2/fs1/gc6159
    fileset_name_seed = fileset_name_or_alias.split("_active")[0]
    storage_filesystem_path = f"{__get_storage2_base_path()}/{fileset_name_seed}"

    return storage_filesystem_path


def fileset_name_to_storage_export_path(fileset_name_or_alias) -> str:
    # TODO I cannot figure out from the code how to populate this.
    fileset_name_seed = fileset_name_or_alias.split("_active")[0]
    export_path = f"{__get_storage2_base_path()}/{fileset_name_seed}"

    return export_path


# TODO what are the protocols for the allocations created from ITSM?
def comment_to_protocols(value: dict) -> list:
    return ["smb"]


"""
    # I was under the impression that nfs was the default; however,
    # after inspecting the migrated allocations, all of them have ["smb"] as the protocol.
    protocols = ["nfs"] # Add nfs always according to business rule

    if value.get("smb_export_name"):
        protocols.append("smb")
    return protocols
"""


def fileset_name_to_storage_name(value) -> str:
    # Examples: fileset_name= "jiaoy_active" --> "jiaoy"
    # fileset_name= "gc6159" --> "gc6159"
    return value.split("_active")[0]


# Example: "akronzer,derek.harford,d.ken,ehogue,jiaoy,perezm,xuebing".split(",")
# return ['akronzer', 'derek.harford', 'd.ken', 'ehogue', 'jiaoy', 'perezm', 'xuebing']
# from this array, create a user from every element in the array
def acl_group_members_to_aggregate_create_users(value) -> Optional[str]:
    if value is None:
        return None

    return value.split(",")


def string_parsing_quota_and_unit_to_integer(value: str) -> int:
    if value is None:
        return

    # all values in ITSM are kept in TB (T) and some in GB (G).
    if value[-1] == "T":
        return int(value[:-1])

    if value[-1] == "G":
        return int(math.ceil(int(value[:-1]) / 1000))

    return


def truthy_or_falsy_to_boolean(value, default_value=None) -> str:
    transfromed_value = __truthy_or_falsy_to_boolean(value, default_value)
    return __boolean_to_coldfront_yes_no(transfromed_value)


def __boolean_to_coldfront_yes_no(value: bool) -> str:
    if value is None:
        return

    if value:
        return "Yes"
    return "No"


# service_provision.audit values: ["0", "1", "false", "true", null]
def __truthy_or_falsy_to_boolean(value, default_value) -> bool:
    if value is None:
        return default_value

    # coerce a boolean value
    if isinstance(value, str):
        if value.lower() == "true":
            return True

        if value.lower() == "false":
            return False

    # throws ValueError: invalid literal for int() with base 10: value
    return bool(int(value))


def __get_storage2_base_path():
    return os.environ.get("STORAGE2_PATH")
