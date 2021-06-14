'''
Admin for ifx
'''
from django.contrib import admin
from ifxuser.admin import UserAdmin
from coldfront.plugins.ifx.models import SuUser

@admin.register(SuUser)
class SuUserAdmin(UserAdmin):
    '''
    Mainly for su-ing
    '''
    change_form_template = "admin/auth/user/change_form.html"
    change_list_template = "admin/auth/user/change_list.html"