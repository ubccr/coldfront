from django.shortcuts import render
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import View

from coldfront.plugins.ldap_user_info.utils import get_user_info


class LDAPUserSearchView(LoginRequiredMixin, View):
    def post(self, request):
        context = {
            'username_exists': False,
            'name': None,
            'email': None,
            'id': request.POST.get('id')
        }

        attributes = get_user_info(request.POST.get('username'), ['displayName', 'mail'])
        display_name = attributes.get('displayName')
        # If one exists so does the other
        if display_name and display_name[0]:
            context['username_exists'] = True
            context['name'] = display_name[0]
            context['email'] = attributes.get('mail')[0]

        return render(request, 'username_search_result.html', context)
