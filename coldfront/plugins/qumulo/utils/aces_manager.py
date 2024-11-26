import hashlib
import json


class AcesManager(object):
    @staticmethod
    def get_base_acl():
        return {
            "control": ["PRESENT"],
            "posix_special_permissions": [],
            "aces": [],
        }

    # readme access perms are now in the default aces variable
    default_aces = [
        {
            "flags": ["CONTAINER_INHERIT"],
            "type": "ALLOWED",
            "trustee": {"name": "File Owner"},
            "rights": [
                "READ",
                "ADD_FILE",
                "ADD_SUBDIR",
                "SYNCHRONIZE",
                "READ_ACL",
                "READ_ATTR",
                "READ_EA",
                "DELETE_CHILD",
                "CHANGE_OWNER",
                "EXECUTE",
                "WRITE_ACL",
                "WRITE_ATTR",
                "WRITE_EA",
            ],
        },
        {
            "flags": ["OBJECT_INHERIT"],
            "type": "ALLOWED",
            "trustee": {"name": "File Owner"},
            "rights": [
                "READ",
                "ADD_FILE",
                "ADD_SUBDIR",
                "SYNCHRONIZE",
                "READ_ACL",
                "READ_ATTR",
                "READ_EA",
                "CHANGE_OWNER",
                "EXECUTE",
                "WRITE_ACL",
                "WRITE_ATTR",
                "WRITE_EA",
            ],
        },
        {
            "flags": ["CONTAINER_INHERIT"],
            "type": "ALLOWED",
            "trustee": {"name": "ris-it-admin", "domain": "ACTIVE_DIRECTORY"},
            "rights": [
                "READ",
                "ADD_FILE",
                "ADD_SUBDIR",
                "SYNCHRONIZE",
                "READ_ACL",
                "READ_ATTR",
                "READ_EA",
                "EXECUTE",
                "DELETE_CHILD",
                "WRITE_ATTR",
                "WRITE_EA",
            ],
        },
        {
            "flags": ["OBJECT_INHERIT"],
            "type": "ALLOWED",
            "trustee": {"name": "ris-it-admin", "domain": "ACTIVE_DIRECTORY"},
            "rights": [
                "READ",
                "ADD_FILE",
                "ADD_SUBDIR",
                "SYNCHRONIZE",
                "READ_ACL",
                "READ_ATTR",
                "READ_EA",
                "EXECUTE",
                "DELETE_CHILD",
                "WRITE_ATTR",
                "WRITE_EA",
            ],
        },
    ]

    everyone_ace = [
        {
            "flags": [],
            "type": "ALLOWED",
            "trustee": {"name": "Everyone"},
            "rights": [
                "READ",
            ],
        },
    ]

    @staticmethod
    def remove_everyone_aces(aces):
        cleaned_aces = []
        for ace in aces:
            trusteeName = ace.get("trustee", {}).get("name", "")
            if trusteeName.upper() == "EVERYONE":
                continue
            cleaned_aces.append(ace)
        return cleaned_aces

    @staticmethod
    def get_allocation_aces(rw_groupname: str, ro_groupname: str):
        return [
            {
                "flags": ["CONTAINER_INHERIT"],
                "type": "ALLOWED",
                "trustee": {
                    "name": rw_groupname,
                    "domain": "ACTIVE_DIRECTORY",
                },
                "rights": [
                    "READ",
                    "SYNCHRONIZE",
                    "READ_ACL",
                    "READ_ATTR",
                    "READ_EA",
                    "EXECUTE",
                    "ADD_FILE",
                    "ADD_SUBDIR",
                    "DELETE_CHILD",
                    "WRITE_ATTR",
                    "WRITE_EA",
                ],
            },
            {
                "flags": ["OBJECT_INHERIT"],
                "type": "ALLOWED",
                "trustee": {
                    "name": rw_groupname,
                    "domain": "ACTIVE_DIRECTORY",
                },
                "rights": [
                    "READ",
                    "SYNCHRONIZE",
                    "READ_ACL",
                    "READ_ATTR",
                    "READ_EA",
                    "EXECUTE",
                    "ADD_FILE",
                    "ADD_SUBDIR",
                    "DELETE_CHILD",
                    "WRITE_ATTR",
                    "WRITE_EA",
                ],
            },
            {
                "flags": ["CONTAINER_INHERIT"],
                "type": "ALLOWED",
                "trustee": {
                    "name": ro_groupname,
                    "domain": "ACTIVE_DIRECTORY",
                },
                "rights": [
                    "READ",
                    "SYNCHRONIZE",
                    "READ_ACL",
                    "READ_ATTR",
                    "READ_EA",
                    "EXECUTE",
                ],
            },
            {
                "flags": ["OBJECT_INHERIT"],
                "type": "ALLOWED",
                "trustee": {
                    "name": ro_groupname,
                    "domain": "ACTIVE_DIRECTORY",
                },
                "rights": [
                    "READ",
                    "SYNCHRONIZE",
                    "READ_ACL",
                    "READ_ATTR",
                    "READ_EA",
                ],
            },
        ]

    @staticmethod
    def get_allocation_file_aces(rw_groupname: str, ro_groupname: str):
        return [
            {
                "flags": [],
                "type": "ALLOWED",
                "trustee": {
                    "name": rw_groupname,
                    "domain": "ACTIVE_DIRECTORY",
                },
                "rights": [
                    "READ",
                    "SYNCHRONIZE",
                    "READ_ACL",
                    "READ_ATTR",
                    "READ_EA",
                    "ADD_FILE",
                    "ADD_SUBDIR",
                    "DELETE_CHILD",
                    "WRITE_ATTR",
                    "WRITE_EA",
                    "EXECUTE",
                ],
            },
            {
                "flags": [],
                "type": "ALLOWED",
                "trustee": {
                    "name": ro_groupname,
                    "domain": "ACTIVE_DIRECTORY",
                },
                "rights": [
                    "READ",
                    "SYNCHRONIZE",
                    "READ_ACL",
                    "READ_ATTR",
                    "READ_EA",
                ],
            },
        ]

    @staticmethod
    def get_traverse_aces(
        rw_groupname: str, ro_groupname: str, is_base_allocation: bool
    ):
        if is_base_allocation:
            return [
                {
                    "flags": ["CONTAINER_INHERIT"],
                    "type": "ALLOWED",
                    "trustee": {
                        "name": rw_groupname,
                        "domain": "ACTIVE_DIRECTORY",
                    },
                    "rights": [
                        "READ",
                        "SYNCHRONIZE",
                        "READ_ACL",
                        "READ_ATTR",
                        "READ_EA",
                        "EXECUTE",
                    ],
                },
                {
                    "flags": ["OBJECT_INHERIT"],
                    "type": "ALLOWED",
                    "trustee": {
                        "name": rw_groupname,
                        "domain": "ACTIVE_DIRECTORY",
                    },
                    "rights": [
                        "READ",
                        "SYNCHRONIZE",
                        "READ_ACL",
                        "READ_ATTR",
                        "READ_EA",
                    ],
                },
                {
                    "flags": ["CONTAINER_INHERIT"],
                    "type": "ALLOWED",
                    "trustee": {
                        "name": ro_groupname,
                        "domain": "ACTIVE_DIRECTORY",
                    },
                    "rights": [
                        "READ",
                        "SYNCHRONIZE",
                        "READ_ACL",
                        "READ_ATTR",
                        "READ_EA",
                        "EXECUTE",
                    ],
                },
                {
                    "flags": ["OBJECT_INHERIT"],
                    "type": "ALLOWED",
                    "trustee": {
                        "name": ro_groupname,
                        "domain": "ACTIVE_DIRECTORY",
                    },
                    "rights": [
                        "READ",
                        "SYNCHRONIZE",
                        "READ_ACL",
                        "READ_ATTR",
                        "READ_EA",
                    ],
                },
            ]
        else:
            return [
                {
                    "flags": [],
                    "type": "ALLOWED",
                    "trustee": {
                        "name": rw_groupname,
                        "domain": "ACTIVE_DIRECTORY",
                    },
                    "rights": [
                        "READ",
                        "SYNCHRONIZE",
                        "READ_ACL",
                        "READ_ATTR",
                        "READ_EA",
                        "EXECUTE",
                    ],
                },
                {
                    "flags": [],
                    "type": "ALLOWED",
                    "trustee": {
                        "name": ro_groupname,
                        "domain": "ACTIVE_DIRECTORY",
                    },
                    "rights": [
                        "READ",
                        "SYNCHRONIZE",
                        "READ_ACL",
                        "READ_ATTR",
                        "READ_EA",
                        "EXECUTE",
                    ],
                },
            ]

    # The aces returned here are "defaults" and reflect the settings for a
    # file that is created in an allocation directory.  Based on the default
    # aces for an allocation directory, the aces are inherited on file creation.

    @staticmethod
    def get_allocation_existing_file_aces(rw_groupname: str, ro_groupname: str):
        return [
            {
                "type": "ALLOWED",
                "flags": [],
                "trustee": {"name": "File Owner"},
                "rights": [
                    "READ",
                    "READ_EA",
                    "READ_ATTR",
                    "READ_ACL",
                    "WRITE_EA",
                    "WRITE_ATTR",
                    "MODIFY",
                    "EXTEND",
                    "EXECUTE",
                    "DELETE_CHILD",
                    # "WRITE_OWNER",
                    "CHANGE_OWNER",
                    # jprew - NOTE: CHANGE_OWNER MIGHT HAVE ODD CONSEQUENCES
                    # double check this
                    "SYNCHRONIZE",
                ],
            },
            {
                "type": "ALLOWED",
                "flags": ["INHERITED"],
                "trustee": {
                    "domain": "ACTIVE_DIRECTORY",
                    "name": "ACCOUNTS\\RIS-IT-ADMIN",
                },
                "rights": [
                    "READ",
                    "READ_EA",
                    "READ_ATTR",
                    "READ_ACL",
                    "WRITE_EA",
                    "WRITE_ATTR",
                    "MODIFY",
                    "EXTEND",
                    "EXECUTE",
                    "DELETE_CHILD",
                    "SYNCHRONIZE",
                ],
            },
            {
                "type": "ALLOWED",
                "flags": ["INHERITED"],
                "trustee": {"domain": "ACTIVE_DIRECTORY", "name": rw_groupname},
                "rights": [
                    "READ",
                    "READ_EA",
                    "READ_ATTR",
                    "READ_ACL",
                    "WRITE_EA",
                    "WRITE_ATTR",
                    "MODIFY",
                    "EXTEND",
                    "EXECUTE",
                    "DELETE_CHILD",
                    "SYNCHRONIZE",
                ],
            },
            {
                "type": "ALLOWED",
                "flags": ["INHERITED"],
                "trustee": {"domain": "ACTIVE_DIRECTORY", "name": ro_groupname},
                "rights": ["READ", "READ_EA", "READ_ATTR", "READ_ACL", "SYNCHRONIZE"],
            },
        ]

    # The aces returned here are "defaults" and reflect the settings for a
    # directory that is created in an allocation directory.  Based on the
    # default aces for an allocation directory, the aces here are inherited
    # upon directory creation.

    @staticmethod
    def get_allocation_existing_directory_aces(rw_groupname: str, ro_groupname: str):
        return [
            {
                "type": "ALLOWED",
                "flags": [],
                "trustee": {"name": "File Owner"},
                "rights": [
                    "READ",
                    "READ_EA",
                    "READ_ATTR",
                    "READ_ACL",
                    "WRITE_EA",
                    "WRITE_ATTR",
                    "EXECUTE",
                    "MODIFY",
                    "EXTEND",
                    "DELETE_CHILD",
                    "SYNCHRONIZE",
                ],
            },
            {
                "type": "ALLOWED",
                "flags": ["CONTAINER_INHERIT", "INHERITED"],
                "trustee": {
                    "domain": "ACTIVE_DIRECTORY",
                    "name": "ACCOUNTS\\RIS-IT-ADMIN",
                },
                "rights": [
                    "READ",
                    "READ_EA",
                    "READ_ATTR",
                    "READ_ACL",
                    "WRITE_EA",
                    "WRITE_ATTR",
                    "EXECUTE",
                    "MODIFY",
                    "EXTEND",
                    "DELETE_CHILD",
                    "SYNCHRONIZE",
                ],
            },
            {
                "type": "ALLOWED",
                "flags": ["OBJECT_INHERIT", "INHERIT_ONLY", "INHERITED"],
                "trustee": {
                    "domain": "ACTIVE_DIRECTORY",
                    "name": "ACCOUNTS\\RIS-IT-ADMIN",
                },
                "rights": [
                    "READ",
                    "READ_EA",
                    "READ_ATTR",
                    "READ_ACL",
                    "WRITE_EA",
                    "WRITE_ATTR",
                    "EXECUTE",
                    "MODIFY",
                    "EXTEND",
                    "DELETE_CHILD",
                    "SYNCHRONIZE",
                ],
            },
            {
                "type": "ALLOWED",
                "flags": ["CONTAINER_INHERIT", "INHERITED"],
                "trustee": {"domain": "ACTIVE_DIRECTORY", "name": rw_groupname},
                "rights": [
                    "READ",
                    "READ_EA",
                    "READ_ATTR",
                    "READ_ACL",
                    "WRITE_EA",
                    "WRITE_ATTR",
                    "EXECUTE",
                    "MODIFY",
                    "EXTEND",
                    "DELETE_CHILD",
                    "SYNCHRONIZE",
                ],
            },
            {
                "type": "ALLOWED",
                "flags": ["OBJECT_INHERIT", "INHERIT_ONLY", "INHERITED"],
                "trustee": {"domain": "ACTIVE_DIRECTORY", "name": rw_groupname},
                "rights": [
                    "READ",
                    "READ_EA",
                    "READ_ATTR",
                    "READ_ACL",
                    "WRITE_EA",
                    "WRITE_ATTR",
                    "MODIFY",
                    "EXTEND",
                    "EXECUTE",
                    "DELETE_CHILD",
                    "SYNCHRONIZE",
                ],
            },
            {
                "type": "ALLOWED",
                "flags": ["CONTAINER_INHERIT", "INHERITED"],
                "trustee": {
                    "domain": "ACTIVE_DIRECTORY",
                    "name": ro_groupname,
                },
                "rights": [
                    "READ",
                    "READ_EA",
                    "READ_ATTR",
                    "READ_ACL",
                    "EXECUTE",
                    "SYNCHRONIZE",
                ],
            },
            {
                "type": "ALLOWED",
                "flags": ["OBJECT_INHERIT", "INHERIT_ONLY", "INHERITED"],
                "trustee": {"domain": "ACTIVE_DIRECTORY", "name": ro_groupname},
                "rights": ["READ", "READ_EA", "READ_ATTR", "READ_ACL", "SYNCHRONIZE"],
            },
        ]

    @staticmethod
    def default_copy():
        return AcesManager.default_aces.copy()

    @staticmethod
    def normalize_trustee(trustee: dict):
        if "name" not in trustee:
            return trustee
        domain = None
        name = trustee["name"].replace("ACCOUNTS\\", "").lower()
        if name == "file owner":
            name = "File Owner"
            domain = "API_INTERNAL_DOMAIN"
        else:
            domain = trustee.get("domain", None)
        normalized_trustee = {"name": name}
        if domain is not None:
            normalized_trustee["domain"] = domain
        return normalized_trustee

    @staticmethod
    def filter_duplicates(aces):
        trustee_hashes = set([])
        cleaned_aces = []
        for ace in aces:
            normalized_trustee = AcesManager.normalize_trustee(ace.get("trustee", {}))
            ace["trustee"] = normalized_trustee
            trustee_hash = AcesManager.sha256(normalized_trustee)
            if trustee_hash in trustee_hashes:
                create_new_ace = True
                for index, cleaned_ace in enumerate(cleaned_aces):
                    if AcesManager.sha256(cleaned_ace["trustee"]) != trustee_hash:
                        continue
                    if sorted(cleaned_ace["flags"]) != sorted(ace["flags"]):
                        continue
                    if cleaned_ace["type"] != ace["type"]:
                        continue
                    cleaned_ace["rights"] = AcesManager.merge_rights(
                        ace["rights"], cleaned_ace["rights"]
                    )
                    cleaned_aces[index] = cleaned_ace
                    create_new_ace = False
                    break
                if create_new_ace:
                    cleaned_aces.append(ace)
            else:
                cleaned_aces.append(ace)
                trustee_hashes.add(trustee_hash)
        return cleaned_aces

    @staticmethod
    def merge_rights(dirty, clean):
        return list(set(dirty).union(set(clean)))

    @staticmethod
    def sha256(value):
        return hashlib.sha256(json.dumps(value).encode("utf-8")).hexdigest()
