import textwrap

from admin_comments.admin import CommentInline
from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from core.djangoapps.grant.models import Grant, GrantFundingAgency


@admin.register(GrantFundingAgency)
class GrantFundingAgencyChoiceAdmin(admin.ModelAdmin):
    list_display = ('name', )


@admin.register(Grant)
class GrantAdmin(admin.ModelAdmin):
    list_display = ['title', 'project', ]
