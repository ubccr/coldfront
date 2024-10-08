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
                "DELETE_CHILD",
                "WRITE_ATTR",
                "WRITE_EA",
            ],
        },
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

    def default_copy(self):
        return self.default_aces.copy()
