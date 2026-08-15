# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin, UserAdmin

from .models import Group, User


@admin.register(User)
class ColdFrontUserAdmin(UserAdmin):
    model = User
    list_display = ["username", "email", "first_name", "last_name", "is_staff"]
    search_fields = ["username"]


@admin.register(Group)
class ColdFrontGroupAdmin(GroupAdmin):
    model = Group
    list_display = ["name", "description"]
    search_fields = ["name"]
