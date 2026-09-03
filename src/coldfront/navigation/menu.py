# SPDX-FileCopyrightText: (C) DigitalOcean, LLC
# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from functools import cache

from django.utils.translation import gettext_lazy as _

from coldfront.registry import registry

from . import Menu, MenuGroup, MenuItem, get_model_item

#
# Nav menus
#

ORGANIZATION_MENU = Menu(
    label=_("Organization"),
    icon_class="fa-solid fa-sitemap",
    groups=(
        MenuGroup(
            label=_("Tenancy"),
            items=(
                get_model_item("tenancy", "tenant", _("Tenants")),
                get_model_item("tenancy", "tenantgroup", _("Tenant Groups")),
            ),
        ),
    ),
)

ALLOCATIONS_MENU = Menu(
    label=_("Allocations"),
    icon_class="fa-solid fa-list-check",
    groups=(
        MenuGroup(
            label=_("Projects"),
            items=(
                get_model_item("ras", "project", _("Projects")),
                get_model_item("ras", "projectuser", _("Project Users")),
                get_model_item("ras", "projectinvite", _("Invites")),
                get_model_item("ris", "publication", _("Publications")),
                get_model_item("ris", "funding", _("Funding")),
            ),
        ),
        MenuGroup(
            label=_("Allocations"),
            items=(
                get_model_item("ras", "allocation", _("Allocations")),
                get_model_item("ras", "allocationchangerequest", _("Change Requests"), actions=("add",)),
                get_model_item("core", "commententry", _("Comment Entries"), actions=[]),
            ),
        ),
    ),
)

RESOURCES_MENU = Menu(
    label=_("Resources"),
    icon_class="fa-solid fa-server",
    groups=(
        MenuGroup(
            label=_("Generic Resources"),
            items=(
                get_model_item("ras", "resource", _("Resources")),
                get_model_item("ras", "resourcetype", _("Resource Types")),
            ),
        ),
        MenuGroup(
            label=_("Slurm"),
            items=(
                get_model_item("slurm", "slurmcluster", _("Slurm Clusters")),
                get_model_item("slurm", "slurmpartition", _("Slurm Partitions")),
                get_model_item("slurm", "slurmaccount", _("Slurm Accounts")),
                get_model_item("slurm", "slurmuser", _("Slurm Users")),
                get_model_item("slurm", "slurmassociation", _("Associations")),
                get_model_item("slurm", "slurmqos", _("QOS")),
                get_model_item("slurm", "slurmaccountusage", _("Usage"), actions=()),
            ),
        ),
        MenuGroup(
            label=_("Storage"),
            items=(
                get_model_item("storage", "storageresource", _("Storage Resources")),
                get_model_item("storage", "storagecluster", _("Storage Clusters")),
                get_model_item("storage", "storagequota", _("Storage Quotas")),
                get_model_item("storage", "storagesnapshotpolicy", _("Snapshot Policies")),
            ),
        ),
    ),
)

CUSTOMIZATION_MENU = Menu(
    label=_("Customization"),
    icon_class="fa-solid fa-sliders",
    groups=(
        MenuGroup(
            label=_("Customization"),
            items=(
                get_model_item("core", "tag", "Tags"),
                get_model_item("core", "customfield", _("Custom Fields")),
                get_model_item("core", "customfieldchoiceset", _("Custom Field Choices")),
                get_model_item("core", "savedfilter", _("Saved Filters")),
                get_model_item("core", "tableconfig", _("Table Configs")),
                get_model_item("core", "customlink", _("Custom Links")),
            ),
        ),
    ),
)

ADMIN_MENU = Menu(
    label=_("Admin"),
    icon_class="fa-solid fa-screwdriver-wrench",
    groups=(
        MenuGroup(
            label=_("Authentication"),
            items=(
                get_model_item("users", "user", _("Users"), staff_only=True),
                get_model_item("users", "group", _("Groups"), staff_only=True),
                get_model_item("users", "role", _("Roles"), actions=["add"]),
                get_model_item("users", "token", _("API Tokens"), staff_only=True),
                get_model_item("users", "objectpermission", _("Permissions"), actions=["add"]),
            ),
        ),
        MenuGroup(
            label=_("System"),
            items=(
                MenuItem(
                    link="core:plugin_list",
                    link_text=_("Plugins"),
                    staff_only=True,
                ),
                MenuItem(
                    link="core:notification_send",
                    link_text=_("Notifications"),
                    staff_only=True,
                ),
                get_model_item("core", "job", _("Jobs"), actions=[]),
            ),
        ),
        MenuGroup(
            label=_("Logging"),
            items=(get_model_item("core", "objectchange", _("Change Log"), actions=[]),),
        ),
    ),
)


BILLING_MENU = Menu(
    label=_("Billing"),
    icon_class="fa-solid fa-receipt",
    groups=(
        MenuGroup(
            label=_("Invoices"),
            items=(get_model_item("billing", "invoice", _("Invoices")),),
        ),
        MenuGroup(
            label=_("Pricing"),
            items=(
                get_model_item("billing", "rate", _("Rates")),
                get_model_item("billing", "freeallowance", _("Free Allowances")),
                get_model_item("billing", "discount", _("Discounts")),
            ),
        ),
    ),
)


@cache
def get_menus():
    """
    Dynamically build and return the list of navigation menus.
    This ensures plugin menus registered during app initialization are included.
    The result is cached since menus don't change without a Django restart.
    """
    menus = [
        ALLOCATIONS_MENU,
        RESOURCES_MENU,
        ORGANIZATION_MENU,
        CUSTOMIZATION_MENU,
        BILLING_MENU,
    ]

    # Add top-level plugin menus
    for menu in registry["plugins"]["menus"]:
        menus.append(menu)

    # Add the default "plugins" menu
    if registry["plugins"]["menu_items"]:
        # Build the default plugins menu
        groups = [MenuGroup(label=label, items=items) for label, items in registry["plugins"]["menu_items"].items()]
        plugins_menu = Menu(label=_("Plugins"), icon_class="fa-solid fa-puzzle-piece", groups=groups)
        menus.append(plugins_menu)

    # Add the admin menu last
    menus.append(ADMIN_MENU)

    return menus
