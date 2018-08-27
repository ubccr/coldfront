import datetime
import textwrap

from admin_comments.admin import CommentInline
from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from simple_history.admin import SimpleHistoryAdmin

from core.djangoapps.subscription.models import (AttributeType, Subscription,
                                                 SubscriptionAttribute,
                                                 SubscriptionAttributeType,
                                                 SubscriptionAttributeUsage,
                                                 SubscriptionStatusChoice,
                                                 SubscriptionUser,
                                                 SubscriptionUserStatusChoice)


@admin.register(SubscriptionStatusChoice)
class SubscriptionStatusChoiceAdmin(admin.ModelAdmin):
    list_display = ('name', )


class SubscriptionUserInline(admin.TabularInline):
    model = SubscriptionUser
    extra = 0
    fields = ('user', 'status', )
    readonly_fields = ('user', )


class SubscriptionAttributeInline(admin.TabularInline):
    model = SubscriptionAttribute
    extra = 0
    fields = ('subscription_attribute_type', 'value', )


@admin.register(Subscription)
class SubscriptionAdmin(SimpleHistoryAdmin):
    readonly_fields_change = ('project', 'justification', 'created', 'modified',)
    fields_change = ('project', 'resources', 'quantity', 'justification',
                     'status', 'active_until', 'created', 'modified',)
    list_display = ('pk', 'project_title', 'project_pi', 'resource', 'quantity',
                    'justification', 'active_until', 'status', 'created', 'modified', )
    inlines = [SubscriptionUserInline, SubscriptionAttributeInline, CommentInline]
    list_filter = ('resources__resource_type__name', 'status', 'resources__name', )
    search_fields = ['project__pi__username', 'project__pi__first_name', 'project__pi__last_name', 'resources__name',
                     'subscriptionuser__user__first_name', 'subscriptionuser__user__last_name', 'subscriptionuser__user__username']
    filter_horizontal = ['resources', ]
    raw_id_fields = ('project',)

    def resource(self, obj):
        return obj.get_parent_resource

    def project_pi(self, obj):
        return obj.project.pi.username

    def project_title(self, obj):
        return textwrap.shorten(obj.project.title, width=50)

    def get_fields(self, request, obj):
        if obj is None:
            return super().get_fields(request)
        else:
            return self.fields_change

    def get_readonly_fields(self, request, obj):
        if obj is None:
            # We are adding an object
            return super().get_readonly_fields(request)
        else:
            return self.readonly_fields_change

    def get_inline_instances(self, request, obj=None):
        if obj is None:
            # We are adding an object
            return []
        else:
            return super().get_inline_instances(request)


@admin.register(AttributeType)
class AttributeTypeAdmin(admin.ModelAdmin):
    list_display = ('name', )


@admin.register(SubscriptionAttributeType)
class SubscriptionAttributeTypeAdmin(admin.ModelAdmin):
    list_display = ('pk', 'name', 'has_usage')


class SubscriptionAttributeUsageInline(admin.TabularInline):
    model = SubscriptionAttributeUsage
    extra = 0


class UsageValueFilter(admin.SimpleListFilter):
    title = _('value')

    parameter_name = 'value'

    def lookups(self, request, model_admin):
        return (
            ('>=0', _('Greater than or equal to 0')),
            ('>10', _('Greater than 10')),
            ('>100', _('Greater than 100')),
            ('>1000', _('Greater than 1000')),
            ('>10000', _('Greater than 10000')),
        )

    def queryset(self, request, queryset):

        if self.value() == '>=0':
            return queryset.filter(subscriptionattributeusage__value__gte=0)

        if self.value() == '>10':
            return queryset.filter(subscriptionattributeusage__value__gte=10)

        if self.value() == '>100':
            return queryset.filter(subscriptionattributeusage__value__gte=100)

        if self.value() == '>1000':
            return queryset.filter(subscriptionattributeusage__value__gte=1000)


@admin.register(SubscriptionAttribute)
class SubscriptionAttributeAdmin(SimpleHistoryAdmin):
    readonly_fields_change = ('subscription', 'subscription_attribute_type', 'created', 'modified', 'project_title')
    fields_change = ('project_title', 'subscription', 'subscription_attribute_type', 'value', 'created', 'modified',)
    list_display = ('pk', 'project', 'pi', 'resource', 'subscription_status',
                    'subscription_attribute_type', 'value', 'usage', 'is_private', 'created', 'modified',)
    inlines = [SubscriptionAttributeUsageInline, ]
    list_filter = (UsageValueFilter, 'subscription_attribute_type',)
    search_fields = (
        'subscription__project__pi__first_name',
        'subscription__project__pi__last_name',
        'subscription__project__pi__username',
        'subscription__subscriptionuser__user__first_name',
        'subscription__subscriptionuser__user__last_name',
        'subscription__subscriptionuser__user__username',
    )

    def usage(self, obj):
        if hasattr(obj, 'subscriptionattributeusage'):
            return obj.subscriptionattributeusage.value
        else:
            return 'N/A'

    def resource(self, obj):
        return obj.subscription.resources.first()

    def subscription_status(self, obj):
        return obj.subscription.status

    def pi(self, obj):
        return '{} {} ({})'.format(obj.subscription.project.pi.first_name, obj.subscription.project.pi.last_name, obj.subscription.project.pi.username)

    def project(self, obj):
        return textwrap.shorten(obj.subscription.project.title, width=50)

    def project_title(self, obj):
        return obj.subscription.project.title

    def get_fields(self, request, obj):
        if obj is None:
            return super().get_fields(request)
        else:
            return self.fields_change

    def get_readonly_fields(self, request, obj):
        if obj is None:
            # We are adding an object
            return super().get_readonly_fields(request)
        else:
            return self.readonly_fields_change

    def get_inline_instances(self, request, obj=None):
        if obj is None:
            # We are adding an object
            return []
        else:
            return super().get_inline_instances(request)


@admin.register(SubscriptionUserStatusChoice)
class SubscriptionUserStatusChoiceAdmin(admin.ModelAdmin):
    list_display = ('name',)


@admin.register(SubscriptionUser)
class SubscriptionUserAdmin(SimpleHistoryAdmin):
    readonly_fields_change = ('subscription', 'user', 'resource', 'created', 'modified',)
    fields_change = ('subscription', 'user', 'status', 'created', 'modified',)
    list_display = ('pk', 'project', 'project_pi', 'resource', 'subscription_status',
                    'user_info', 'status', 'created', 'modified',)
    inlines_change = [CommentInline, ]
    list_filter = ('status', 'subscription__status', 'subscription__resources',)
    search_fields = (
        'user__first_name',
        'user__last_name',
        'user__username',
    )

    def subscription_status(self, obj):
        return obj.subscription.status

    def user_info(self, obj):
        return '{} {} ({})'.format(obj.user.first_name, obj.user.last_name, obj.user.username)

    def resource(self, obj):
        return obj.subscription.resources.first()

    def project_pi(self, obj):
        return obj.subscription.project.pi

    def project(self, obj):
        return textwrap.shorten(obj.subscription.project.title, width=50)

    def get_fields(self, request, obj):
        if obj is None:
            return super().get_fields(request)
        else:
            return self.fields_change

    def get_readonly_fields(self, request, obj):
        if obj is None:
            # We are adding an object
            return super().get_readonly_fields(request)
        else:
            return self.readonly_fields_change

    def get_inline_instances(self, request, obj=None):
        if obj is None:
            # We are adding an object
            return []
        else:
            return super().get_inline_instances(request)


class ValueFilter(admin.SimpleListFilter):
    title = _('value')

    parameter_name = 'value'

    def lookups(self, request, model_admin):
        return (
            ('>0', _('Greater than > 0')),
            ('>10', _('Greater than > 10')),
            ('>100', _('Greater than > 100')),
            ('>1000', _('Greater than > 1000')),
        )

    def queryset(self, request, queryset):

        if self.value() == '>0':
            return queryset.filter(value__gt=0)

        if self.value() == '>10':
            return queryset.filter(value__gt=10)

        if self.value() == '>100':
            return queryset.filter(value__gt=100)

        if self.value() == '>1000':
            return queryset.filter(value__gt=1000)


@admin.register(SubscriptionAttributeUsage)
class SubscriptionAttributeUsageAdmin(SimpleHistoryAdmin):
    list_display = ('subscription_attribute', 'resource', 'value',)
    readonly_fields = ('subscription_attribute',)
    fields = ('subscription_attribute', 'value',)
    list_filter = ('subscription_attribute__subscription_attribute_type', 'subscription_attribute__subscription__resources', ValueFilter, )

    def resource(self, obj):
        return obj.subscription_attribute.subscription.resources.first().name
