# SPDX-FileCopyrightText: (C) ColdFront Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from coldfront.core.grant.models import Grant, GrantFundingAgency


@admin.register(GrantFundingAgency)
class GrantFundingAgencyChoiceAdmin(admin.ModelAdmin):
    list_display = ("name",)


@admin.register(Grant)
class GrantAdmin(SimpleHistoryAdmin):
    readonly_fields = (
        "project",
        "created",
        "modified",
    )
    fields = (
        "project",
        "title",
        "grant_number",
        "role",
        "grant_pi_full_name",
        "funding_agency",
        "other_funding_agency",
        "other_award_number",
        "grant_start",
        "grant_end",
        "percent_credit",
        "direct_funding",
        "total_amount_awarded",
        "status",
        "created",
        "modified",
    )
    list_display = [
        "title",
        "Project_PI",
        "role",
        "grant_pi_full_name",
        "Funding_Agency",
        "status",
        "grant_end",
    ]
    list_filter = ("funding_agency", "role", "status", "grant_end")
    search_fields = [
        "project__title",
        "project__pi__username",
        "project__pi__first_name",
        "project__pi__last_name",
        "funding_agency__name",
        "grant_pi_full_name",
    ]

    def Project_PI(self, obj):
        return "{} {} ({})".format(obj.project.pi.first_name, obj.project.pi.last_name, obj.project.pi.username)

    def Funding_Agency(self, obj):
        if obj.funding_agency.name == "Other":
            return obj.other_funding_agency
        else:
            return obj.funding_agency.name
