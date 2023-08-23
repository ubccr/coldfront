from django.contrib import admin
from django import forms

from allauth.account.models import EmailAddress

from coldfront.core.user.models import IdentityLinkingRequestStatusChoice
from coldfront.core.user.models import IdentityLinkingRequest
from coldfront.core.user.models import UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('username', 'first_name', 'last_name', 'is_pi')
    ordering = ('user__username', 'user__last_name')
    list_filter = ('is_pi',)
    search_fields = ['user__username', 'user__first_name', 'user__last_name']

    def username(self, obj):
        return obj.user.username

    def first_name(self, obj):
        return obj.user.first_name

    def last_name(self, obj):
        return obj.user.last_name


class EmailAddressInlineFormset(forms.models.BaseInlineFormSet):

    def clean(self):
        """Ensure that exactly one address is set as the primary for a
        particular user."""
        super().clean()
        num_primary = 0
        for form in self.forms:
            if form.cleaned_data.get('primary'):
                num_primary += 1
        if num_primary != 1:
            raise forms.ValidationError(
                'Exactly one address must be primary.')


class EmailAddressInline(admin.TabularInline):
    model = EmailAddress
    extra = 0
    formset = EmailAddressInlineFormset


admin.site.register(IdentityLinkingRequest)
admin.site.register(IdentityLinkingRequestStatusChoice)
