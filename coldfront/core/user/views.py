from argparse import ArgumentError
import logging
import re
from typing import List

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.models import User
from django.db.models import BooleanField, Prefetch
from django.db.models.expressions import ExpressionWrapper, F, Q
from django.db.models.functions import Lower
from django.forms import ValidationError, formset_factory
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import ListView, TemplateView

from coldfront.core.project.models import Project, ProjectUser
from coldfront.core.user.forms import UserOrcidEditForm, UserSearchForm, UserSelectForm, UserSelectResultForm
from coldfront.core.user.models import UserProfile
from coldfront.core.user.utils import CombinedUserSearch
from coldfront.core.utils.common import import_from_settings
from coldfront.core.utils.mail import send_email_template

logger = logging.getLogger(__name__)
EMAIL_ENABLED = import_from_settings('EMAIL_ENABLED', False)
if EMAIL_ENABLED:
    EMAIL_TICKET_SYSTEM_ADDRESS = import_from_settings(
        'EMAIL_TICKET_SYSTEM_ADDRESS')


@method_decorator(login_required, name='dispatch')
class UserProfileView(TemplateView):
    template_name = 'user/user_profile.html'

    def dispatch(self, request, *args, viewed_username=None, **kwargs):
        # viewing another user profile requires permissions
        if viewed_username:
            if request.user.is_superuser or request.user.is_staff:
                # allow, via fallthrough
                pass
            else:
                # redirect them to their own profile

                # error if they tried to do something naughty
                if not request.user.username == viewed_username:
                    messages.error(request, "You aren't allowed to view other user profiles!")
                # if they used their own username, no need to provide an error - just redirect

                return HttpResponseRedirect(reverse('user-profile'))

        return super().dispatch(request, *args, viewed_username=viewed_username, **kwargs)

    def get_context_data(self, viewed_username=None, **kwargs):
        context = super().get_context_data(**kwargs)

        if viewed_username:
            viewed_user = get_object_or_404(User, username=viewed_username)
        else:
            viewed_user = self.request.user
        
        viewed_user_profile: UserProfile = UserProfile.objects.get(user_id = viewed_user.id)

        group_list = ', '.join(
            [group.name for group in viewed_user.groups.all()])
        

        iod_keys = [f"orcid{i}" for i in range(1, 5)]
        
        if viewed_user_profile.orcid_id != None:
            iod_vals = viewed_user_profile.orcid_id.split('-')
            init_orcid_data = { k:v for (k,v) in zip(iod_keys, iod_vals) }
        else:
            init_orcid_data = { k:"" for k in iod_keys }
        
        init_orcid_data['username'] = viewed_user.username

        context['group_list'] = group_list
        context['viewed_user'] = viewed_user
        context['orcid_edit_form'] = UserOrcidEditForm(initial=init_orcid_data)
        return context
    
    def post(self, request, *args, **kwargs):
        form = UserOrcidEditForm(request.POST)
        viewed_username = request.POST['username']
        viewed_user = get_object_or_404(User, username=viewed_username)

        if form.is_valid():
            profile_cleaned = form.cleaned_data
            orcids = [profile_cleaned[f"orcid{i}"] for i in range(1, 5)]

            viewed_user_profile: UserProfile = UserProfile.objects.get(user_id=viewed_user.id)
            viewed_user_profile.orcid_id = '-'.join(orcids)
            
            try:
                viewed_user_profile.save()
                messages.success(request, "ORCID successfully updated.")
            except ValidationError as e:
                messages.error(request, e.message)
        
        return HttpResponseRedirect(reverse('user-profile', kwargs={'viewed_username': viewed_username}))


@method_decorator(login_required, name='dispatch')
class UserProjectsManagersView(ListView):
    template_name = 'user/user_projects_managers.html'

    def dispatch(self, request, *args, viewed_username=None, **kwargs):
        # viewing another user requires permissions
        if viewed_username:
            if request.user.is_superuser or request.user.is_staff:
                # allow, via fallthrough
                pass
            else:
                # redirect them to their own page

                # error if they tried to do something naughty
                if not request.user.username == viewed_username:
                    messages.error(request, "You aren't allowed to view projects for other users!")
                # if they used their own username, no need to provide an error - just redirect

                return HttpResponseRedirect(reverse('user-projects-managers'))

        # get_queryset does not get kwargs, so we need to store it off here
        if viewed_username:
            self.viewed_user = get_object_or_404(User, username=viewed_username)
        else:
            self.viewed_user = self.request.user

        return super().dispatch(request, *args, viewed_username=viewed_username, **kwargs)

    def get_queryset(self, *args, **kwargs):
        viewed_user = self.viewed_user

        ongoing_projectuser_statuses = (
            'Active',
            'Pending - Add',
            'Pending - Remove',
        )
        ongoing_project_statuses = (
            'New',
            'Active',
        )

        qs = ProjectUser.objects.filter(
            user=viewed_user,
            status__name__in=ongoing_projectuser_statuses,
            project__status__name__in=ongoing_project_statuses,
        ).select_related(
            'status',
            'role',
            'project',
            'project__status',
            'project__field_of_science',
            'project__pi',
        ).only(
            'status__name',
            'role__name',
            'project__title',
            'project__status__name',
            'project__field_of_science__description',
            'project__pi__username',
            'project__pi__first_name',
            'project__pi__last_name',
            'project__pi__email',
        ).annotate(
            is_project_pi=ExpressionWrapper(
                Q(user=F('project__pi')),
                output_field=BooleanField(),
            ),
            is_project_manager=ExpressionWrapper(
                Q(role__name='Manager'),
                output_field=BooleanField(),
            ),
        ).order_by(
            '-is_project_pi',
            '-is_project_manager',
            Lower('project__pi__username').asc(),
            Lower('project__title').asc(),
            # unlikely things will get to this point unless there's almost-duplicate projects
            '-project__pk',  # more performant stand-in for '-project__created'
        ).prefetch_related(
            Prefetch(
                lookup='project__projectuser_set',
                queryset=ProjectUser.objects.filter(
                    role__name='Manager',
                    status__name__in=ongoing_projectuser_statuses,
                ).exclude(
                    user__pk__in=[
                        F('project__pi__pk'),  # we assume pi is 'Manager' or can act like one - no need to list twice
                        viewed_user.pk,  # we display elsewhere if the user is a manager of this project
                    ],
                ).select_related(
                    'status',
                    'user',
                ).only(
                    'status__name',
                    'user__username',
                    'user__first_name',
                    'user__last_name',
                    'user__email',
                ).order_by(
                    'user__username',
                ),
                to_attr='project_managers',
            ),
        )

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['viewed_user'] = self.viewed_user

        if self.request.user == self.viewed_user:
            context['user_pronounish'] = 'You'
            context['user_verbform_be'] = 'are'
        else:
            context['user_pronounish'] = 'This user'
            context['user_verbform_be'] = 'is'

        return context


class UserUpgradeAccount(LoginRequiredMixin, UserPassesTestMixin, View):

    def test_func(self):
        return True

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_superuser:
            messages.error(request, 'You are already a super user')
            return HttpResponseRedirect(reverse('user-profile'))

        if request.user.userprofile.is_pi:
            messages.error(request, 'Your account has already been upgraded')
            return HttpResponseRedirect(reverse('user-profile'))

        return super().dispatch(request, *args, **kwargs)

    def post(self, request):
        if EMAIL_ENABLED:
            send_email_template(
                'Upgrade Account Request',
                'email/upgrade_account_request.txt',
                {'user': request.user},
                request.user.email,
                [EMAIL_TICKET_SYSTEM_ADDRESS]
            )

        messages.success(request, 'Your request has been sent')
        return HttpResponseRedirect(reverse('user-profile'))


class UserSearchHome(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'user/user_search_home.html'

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context['user_search_form'] = UserSearchForm()
        return context

    def test_func(self):
        return self.request.user.is_staff


class UserSearchResults(LoginRequiredMixin, UserPassesTestMixin, View):
    template_name = 'user/user_search_results.html'
    raise_exception = True

    def post(self, request):
        user_search_string = request.POST.get('q')

        search_by = request.POST.get('search_by')

        cobmined_user_search_obj = CombinedUserSearch(
            user_search_string, search_by)
        context = cobmined_user_search_obj.search()

        return render(request, self.template_name, context)

    def test_func(self):
        return self.request.user.is_staff


class UserSelectHome(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'user/user_select_home.html'

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context['user_select_form'] = UserSelectForm()
        return context

    def test_func(self):
        return self.request.user.is_staff


class UserSelectResults(LoginRequiredMixin, UserPassesTestMixin, View):
    """
    Expects "user_select_avail_ids" (List[int]: list of selectable user ids)
    and "user_select_redirect" (str: where to redirect to after selection is made).
    If "user_select_avail" is not provided, defaults to all users.

    Places all selected user pks into request.session['user_select_selected'].
    """
    template_name = 'user/user_select_results.html'
    AVAIL_KEY = "user_select_avail_ids"
    REDIRECT_KEY = "user_select_redirect"
    SELECTED_KEY = "user_select_selected"

    _user_dict_values = [
        "username", "first_name", "last_name", "email"
    ]

    def filter_users(self, users: List[User], query: str, search_by: str, search_options: List[str]) -> List[str]:
        """
        Filters the list of users based on the search options.
        """
        search_thru_values = ["username"] if 'exact_username' in search_by else self._user_dict_values
        re_flags = re.IGNORECASE if 'ignore_case' in search_options else 0
        query_list = query.split()
        filtered_users = []

        for user in users:
            matched = False

            for search_value_str in search_thru_values:
                search_val = getattr(user, search_value_str)

                for query in query_list:
                    if 'regex' in search_options:
                        if 'match_whole_word' in search_options:
                            matched = re.match(query, search_val, re_flags) is not None
                        else:
                            matched = re.search(query, search_val, re_flags) is not None
                    else:
                        if 'match_whole_word' in search_options:
                            if re_flags == re.IGNORECASE:
                                matched = search_val.lower() == query.lower()
                            else:
                                matched = search_val == query
                        else:
                            if re_flags == re.IGNORECASE:
                                matched = query.lower() in search_val.lower()
                            else:
                                matched = query in search_val
                    
                    if matched:
                        break
                
                if matched:
                    break
            
            
            if matched:
                user_dict = {}
                for value in self._user_dict_values:
                    user_dict[value] = getattr(user, value)
                filtered_users.append(user_dict)

        return filtered_users

    def post(self, request, *args, **kwargs):
        if self.REDIRECT_KEY not in request.session:
            raise ValueError(f"'{self.REDIRECT_KEY}' not in request.session")
        if "select_users" in request.POST:
            # Submit button pressed
            filtered_users: List = request.session.pop('user_select_filtered', [])
            formset = formset_factory(UserSelectResultForm, max_num=len(filtered_users))
            formset = formset(request.POST, initial=filtered_users, prefix='userform')
            selected_users = []

            if formset.is_valid():
                for form in formset:
                    user_form_data = form.cleaned_data
                    if user_form_data['selected']:
                        user: User = User.objects.get(username=user_form_data['username'])
                        selected_users.append(user.pk)
            
            request.session[self.SELECTED_KEY] = selected_users
            return HttpResponseRedirect(request.session.get(self.REDIRECT_KEY))
        else:
            # Initial load
            query = request.POST.get('query')
            search_by = request.POST.get('search_by')
            search_options = request.POST.getlist('search_options[]')

            # List of users to filter
            avail_user_ids = request.session.pop(self.AVAIL_KEY, list(User.objects.all().values_list('pk', flat=True)))
            avail_users = User.objects.filter(pk__in=avail_user_ids)
            filtered_users = self.filter_users(avail_users, query, search_by, search_options)
            request.session['user_select_filtered'] = filtered_users

            formset = formset_factory(UserSelectResultForm, max_num=len(filtered_users))
            formset = formset(initial=filtered_users, prefix='userform')
            context = {
                "matches": filtered_users,
                "formset": formset,
                "redirect": request.session.get(self.REDIRECT_KEY, "")
            }

            return render(request, self.template_name, context)

    def test_func(self):
        return self.request.user.is_staff


class UserListAllocations(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'user/user_list_allocations.html'

    def test_func(self):
        return self.request.user.is_superuser or self.request.user.userprofile.is_pi

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)

        user_dict = {}

        for project in Project.objects.filter(pi=self.request.user):
            for allocation in project.allocation_set.filter(status__name='Active'):
                for allocation_user in allocation.allocationuser_set.filter(status__name='Active').order_by('user__username'):
                    if allocation_user.user not in user_dict:
                        user_dict[allocation_user.user] = []

                    user_dict[allocation_user.user].append(allocation)

        context['user_dict'] = user_dict

        return context
