from ldap3 import Server, Connection, ALL, NTLM, MODIFY_DELETE
from ldap3.extend.microsoft.addMembersToGroups import (
    ad_add_members_to_groups,
)

import os
from dotenv import load_dotenv

load_dotenv(override=True)


class ActiveDirectoryAPI:
    def __init__(self) -> None:
        serverName = os.environ.get("AD_SERVER_NAME")
        adUser = os.environ.get("AD_USERNAME")
        adUserPwd = os.environ.get("AD_USER_PASS")

        server = Server(host=serverName, use_ssl=True, get_info=ALL)
        self.conn = Connection(
            server,
            user="ACCOUNTS\\" + adUser,
            password=adUserPwd,
            authentication=NTLM,
        )

        if not self.conn.bind():
            raise self.conn.result

    def get_user(self, wustlkey: str):
        if not wustlkey:
            raise ValueError(("wustlkey must be defined"))

        self.conn.search(
            "dc=accounts,dc=ad,dc=wustl,dc=edu",
            f"(&(objectclass=person)(sAMAccountName={wustlkey}))",
            attributes=["sAMAccountName", "mail", "givenName", "sn"],
        )

        if not self.conn.response:
            raise ValueError("Invalid wustlkey")

        return self.conn.response[0]

    def get_user_by_email(self, email: str):
        if not email:
            raise ValueError(("email must be defined"))

        self.conn.search(
            "dc=accounts,dc=ad,dc=wustl,dc=edu",
            f"(&(objectclass=person)(mail={email}))",
            attributes=["sAMAccountName", "mail", "givenName", "sn"],
        )

        if not self.conn.response:
            raise ValueError("Invalid email")

        return self.conn.response[0]

    def create_ad_group(self, group_name: str) -> None:
        new_group_DN = self.generate_group_dn(group_name)

        self.conn.add(
            new_group_DN,
            "group",
            attributes={"sAMAccountName": group_name},
        )

    def add_user_to_ad_group(self, wustlkey: str, group_name: str):
        group_dn = self.get_group_dn(group_name)

        user = self.get_user(wustlkey)
        user_dn = user["dn"]

        ad_add_members_to_groups(self.conn, user_dn, group_dn)

    def get_group_dn(self, group_name: str) -> str:
        groups_OU = os.environ.get("AD_GROUPS_OU")
        self.conn.search(
            groups_OU, f"(&(objectclass=group)(sAMAccountName={group_name}))"
        )

        if not self.conn.response:
            raise ValueError("Invalid group_name")

        return self.conn.response[0]["dn"]

    def delete_ad_group(self, group_name: str):
        group_dn = self.get_group_dn(group_name)

        return self.conn.delete(group_dn)

    def remove_user_from_group(self, user_name: str, group_name: str):
        user_dn = self.get_user(user_name)["dn"]
        group_dn = self.get_group_dn(group_name)

        self.conn.modify(group_dn, {"member": [(MODIFY_DELETE, [user_dn])]})

    @staticmethod
    def generate_group_dn(group_name: str) -> str:
        groups_OU = os.environ.get("AD_GROUPS_OU")
        return f"cn={group_name},{groups_OU}"
