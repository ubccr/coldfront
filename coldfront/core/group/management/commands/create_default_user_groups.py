from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission

# Default permissions for the RIS-UserSupport user_group
DEFAULT_RIS_USERSUPPORT_GROUP_PROJECT_PERMISSIONS = [
    {"id": 53, "codename": "add_project"},
    {"id": 54, "codename": "change_project"},
    {"id": 55, "codename": "delete_project"},
    {"id": 56, "codename": "view_project"},
    {"id": 57, "codename": "can_view_all_projects"},
    {"id": 58, "codename": "can_review_pending_project_reviews"},
    {"id": 59, "codename": "add_projectreviewstatuschoice"},
    {"id": 60, "codename": "change_projectreviewstatuschoice"},
    {"id": 61, "codename": "delete_projectreviewstatuschoice"},
    {"id": 62, "codename": "view_projectreviewstatuschoice"},
    {"id": 63, "codename": "add_projectstatuschoice"},
    {"id": 64, "codename": "change_projectstatuschoice"},
    {"id": 65, "codename": "delete_projectstatuschoice"},
    {"id": 66, "codename": "view_projectstatuschoice"},
    {"id": 67, "codename": "add_projectuserrolechoice"},
    {"id": 68, "codename": "change_projectuserrolechoice"},
    {"id": 69, "codename": "delete_projectuserrolechoice"},
    {"id": 70, "codename": "view_projectuserrolechoice"},
    {"id": 71, "codename": "add_projectuserstatuschoice"},
    {"id": 72, "codename": "change_projectuserstatuschoice"},
    {"id": 73, "codename": "delete_projectuserstatuschoice"},
    {"id": 74, "codename": "view_projectuserstatuschoice"},
    {"id": 75, "codename": "add_projectusermessage"},
    {"id": 76, "codename": "change_projectusermessage"},
    {"id": 77, "codename": "delete_projectusermessage"},
    {"id": 78, "codename": "view_projectusermessage"},
    {"id": 79, "codename": "add_projectreview"},
    {"id": 80, "codename": "change_projectreview"},
    {"id": 81, "codename": "delete_projectreview"},
    {"id": 82, "codename": "view_projectreview"},
    {"id": 83, "codename": "add_projectadmincomment"},
    {"id": 84, "codename": "change_projectadmincomment"},
    {"id": 85, "codename": "delete_projectadmincomment"},
    {"id": 86, "codename": "view_projectadmincomment"},
    {"id": 87, "codename": "add_historicalprojectuser"},
    {"id": 88, "codename": "change_historicalprojectuser"},
    {"id": 89, "codename": "delete_historicalprojectuser"},
    {"id": 90, "codename": "view_historicalprojectuser"},
    {"id": 91, "codename": "add_historicalprojectreview"},
    {"id": 92, "codename": "change_historicalprojectreview"},
    {"id": 93, "codename": "delete_historicalprojectreview"},
    {"id": 94, "codename": "view_historicalprojectreview"},
    {"id": 95, "codename": "add_historicalproject"},
    {"id": 96, "codename": "change_historicalproject"},
    {"id": 97, "codename": "delete_historicalproject"},
    {"id": 98, "codename": "view_historicalproject"},
    {"id": 99, "codename": "add_projectuser"},
    {"id": 100, "codename": "change_projectuser"},
    {"id": 101, "codename": "delete_projectuser"},
    {"id": 102, "codename": "view_projectuser"},
    {"id": 103, "codename": "add_attributetype"},
    {"id": 104, "codename": "change_attributetype"},
    {"id": 105, "codename": "delete_attributetype"},
    {"id": 106, "codename": "view_attributetype"},
    {"id": 107, "codename": "add_projectattribute"},
    {"id": 108, "codename": "change_projectattribute"},
    {"id": 109, "codename": "delete_projectattribute"},
    {"id": 110, "codename": "view_projectattribute"},
    {"id": 111, "codename": "add_projectattributeusage"},
    {"id": 112, "codename": "change_projectattributeusage"},
    {"id": 113, "codename": "delete_projectattributeusage"},
    {"id": 114, "codename": "view_projectattributeusage"},
    {"id": 115, "codename": "add_projectattributetype"},
    {"id": 116, "codename": "change_projectattributetype"},
    {"id": 117, "codename": "delete_projectattributetype"},
    {"id": 118, "codename": "view_projectattributetype"},
    {"id": 119, "codename": "add_historicalprojectattributeusage"},
    {"id": 120, "codename": "change_historicalprojectattributeusage"},
    {"id": 121, "codename": "delete_historicalprojectattributeusage"},
    {"id": 122, "codename": "view_historicalprojectattributeusage"},
    {"id": 123, "codename": "add_historicalprojectattributetype"},
    {"id": 124, "codename": "change_historicalprojectattributetype"},
    {"id": 125, "codename": "delete_historicalprojectattributetype"},
    {"id": 126, "codename": "view_historicalprojectattributetype"},
    {"id": 127, "codename": "add_historicalprojectattribute"},
    {"id": 128, "codename": "change_historicalprojectattribute"},
    {"id": 129, "codename": "delete_historicalprojectattribute"},
    {"id": 130, "codename": "view_historicalprojectattribute"},
]
DEFAULT_RIS_USERSUPPORT_GROUP_ALLOCATION_PERMISSIONS = [
    {"id": 167, "codename": "add_allocation"},
    {"id": 168, "codename": "change_allocation"},
    {"id": 169, "codename": "delete_allocation"},
    {"id": 170, "codename": "view_allocation"},
    {"id": 171, "codename": "can_view_all_allocations"},
    {"id": 172, "codename": "can_review_allocation_requests"},
    {"id": 173, "codename": "can_manage_invoice"},
    {"id": 177, "codename": "view_allocationattribute"},
    {"id": 181, "codename": "view_allocationattributetype"},
    {"id": 185, "codename": "view_allocationstatuschoice"},
    {"id": 189, "codename": "view_allocationuserstatuschoice"},
    {"id": 193, "codename": "view_attributetype"},
    {"id": 194, "codename": "add_allocationattributeusage"},
    {"id": 195, "codename": "change_allocationattributeusage"},
    {"id": 196, "codename": "delete_allocationattributeusage"},
    {"id": 197, "codename": "view_allocationattributeusage"},
    {"id": 198, "codename": "add_historicalallocationuser"},
    {"id": 199, "codename": "change_historicalallocationuser"},
    {"id": 200, "codename": "delete_historicalallocationuser"},
    {"id": 201, "codename": "view_historicalallocationuser"},
    {"id": 202, "codename": "add_historicalallocationattributeusage"},
    {"id": 203, "codename": "change_historicalallocationattributeusage"},
    {"id": 204, "codename": "delete_historicalallocationattributeusage"},
    {"id": 205, "codename": "view_historicalallocationattributeusage"},
    {"id": 206, "codename": "add_historicalallocationattributetype"},
    {"id": 207, "codename": "change_historicalallocationattributetype"},
    {"id": 208, "codename": "delete_historicalallocationattributetype"},
    {"id": 209, "codename": "view_historicalallocationattributetype"},
    {"id": 210, "codename": "add_historicalallocationattribute"},
    {"id": 211, "codename": "change_historicalallocationattribute"},
    {"id": 212, "codename": "delete_historicalallocationattribute"},
    {"id": 213, "codename": "view_historicalallocationattribute"},
    {"id": 214, "codename": "add_historicalallocation"},
    {"id": 215, "codename": "change_historicalallocation"},
    {"id": 216, "codename": "delete_historicalallocation"},
    {"id": 217, "codename": "view_historicalallocation"},
    {"id": 218, "codename": "add_allocationusernote"},
    {"id": 219, "codename": "change_allocationusernote"},
    {"id": 220, "codename": "delete_allocationusernote"},
    {"id": 221, "codename": "view_allocationusernote"},
    {"id": 222, "codename": "add_allocationuser"},
    {"id": 223, "codename": "change_allocationuser"},
    {"id": 224, "codename": "delete_allocationuser"},
    {"id": 225, "codename": "view_allocationuser"},
    {"id": 226, "codename": "add_allocationadminnote"},
    {"id": 227, "codename": "change_allocationadminnote"},
    {"id": 228, "codename": "delete_allocationadminnote"},
    {"id": 229, "codename": "view_allocationadminnote"},
    {"id": 230, "codename": "add_allocationaccount"},
    {"id": 231, "codename": "change_allocationaccount"},
    {"id": 232, "codename": "delete_allocationaccount"},
    {"id": 233, "codename": "view_allocationaccount"},
    {"id": 234, "codename": "add_allocationchangerequest"},
    {"id": 235, "codename": "change_allocationchangerequest"},
    {"id": 236, "codename": "delete_allocationchangerequest"},
    {"id": 237, "codename": "view_allocationchangerequest"},
    {"id": 238, "codename": "add_allocationchangestatuschoice"},
    {"id": 239, "codename": "change_allocationchangestatuschoice"},
    {"id": 240, "codename": "delete_allocationchangestatuschoice"},
    {"id": 241, "codename": "view_allocationchangestatuschoice"},
    {"id": 242, "codename": "add_historicalallocationchangerequest"},
    {"id": 243, "codename": "change_historicalallocationchangerequest"},
    {"id": 244, "codename": "delete_historicalallocationchangerequest"},
    {"id": 245, "codename": "view_historicalallocationchangerequest"},
    {"id": 246, "codename": "add_historicalallocationattributechangerequest"},
    {"id": 247, "codename": "change_historicalallocationattributechangerequest"},
    {"id": 248, "codename": "delete_historicalallocationattributechangerequest"},
    {"id": 249, "codename": "view_historicalallocationattributechangerequest"},
    {"id": 250, "codename": "add_allocationattributechangerequest"},
    {"id": 251, "codename": "change_allocationattributechangerequest"},
    {"id": 252, "codename": "delete_allocationattributechangerequest"},
    {"id": 253, "codename": "view_allocationattributechangerequest"},
]

# Combine all permissions for the RIS-UserSupport user_group
DEFAULT_RIS_USERSUPPORT_GROUP_PERMISSIONS = (
    DEFAULT_RIS_USERSUPPORT_GROUP_PROJECT_PERMISSIONS
    + DEFAULT_RIS_USERSUPPORT_GROUP_ALLOCATION_PERMISSIONS
)
# Default user groups
DEFAULT_RIS_USER_GROUPS = [
    {
        "name": "RIS-UserSupport",
        "permissions": DEFAULT_RIS_USERSUPPORT_GROUP_PERMISSIONS,
    }
]


class Command(BaseCommand):
    """
    Command to create default user groups.
    """

    help = "Create default user groups"

    def handle(self, *args, **options):
        print("Creating default user groups ...")
        for user_group in DEFAULT_RIS_USER_GROUPS:
            new_user_group, _ = Group.objects.get_or_create(name=user_group["name"])
            permission_query_set = Permission.objects.filter(
                id__in=[permission["id"] for permission in user_group["permissions"]]
            ).all()
            new_user_group.permissions.add(*permission_query_set)

        print("Finished creating default user groups")
