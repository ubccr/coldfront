# SPDX-FileCopyrightText: (C) ColdFront Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.models import User
from django.db.models import BooleanField, Prefetch
from django.db.models.expressions import ExpressionWrapper, F, Q
from django.db.models.functions import Lower
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import ListView, TemplateView

from coldfront.core.project.models import Project, ProjectUser
from coldfront.core.user.forms import UserSearchForm
from coldfront.core.user.utils import CombinedUserSearch
from coldfront.core.utils.common import import_from_settings
from coldfront.core.utils.mail import send_email_template

logger = logging.getLogger(__name__)
EMAIL_ENABLED = import_from_settings("EMAIL_ENABLED", False)
if EMAIL_ENABLED:
    EMAIL_SENDER = import_from_settings("EMAIL_SENDER")
    EMAIL_TICKET_SYSTEM_ADDRESS = import_from_settings("EMAIL_TICKET_SYSTEM_ADDRESS")


@method_decorator(login_required, name="dispatch")
class UserProfile(TemplateView):
    template_name = "user/user_profile.html"

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

                return HttpResponseRedirect(reverse("user-profile"))

        return super().dispatch(request, *args, viewed_username=viewed_username, **kwargs)

    def get_context_data(self, viewed_username=None, **kwargs):
        context = super().get_context_data(**kwargs)

        if viewed_username:
            viewed_user = get_object_or_404(User, username=viewed_username)
        else:
            viewed_user = self.request.user

        group_list = ", ".join([group.name for group in viewed_user.groups.all()])
        context["group_list"] = group_list
        context["viewed_user"] = viewed_user
        return context


@method_decorator(login_required, name="dispatch")
class UserProjectsManagersView(ListView):
    template_name = "user/user_projects_managers.html"

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

                return HttpResponseRedirect(reverse("user-projects-managers"))

        # get_queryset does not get kwargs, so we need to store it off here
        if viewed_username:
            self.viewed_user = get_object_or_404(User, username=viewed_username)
        else:
            self.viewed_user = self.request.user

        return super().dispatch(request, *args, viewed_username=viewed_username, **kwargs)

    def get_queryset(self, *args, **kwargs):
        viewed_user = self.viewed_user

        ongoing_projectuser_statuses = (
            "Active",
            "Pending - Add",
            "Pending - Remove",
        )
        ongoing_project_statuses = (
            "New",
            "Active",
        )

        qs = (
            ProjectUser.objects.filter(
                user=viewed_user,
                status__name__in=ongoing_projectuser_statuses,
                project__status__name__in=ongoing_project_statuses,
            )
            .select_related(
                "status",
                "role",
                "project",
                "project__status",
                "project__field_of_science",
                "project__pi",
            )
            .only(
                "status__name",
                "role__name",
                "project__title",
                "project__status__name",
                "project__field_of_science__description",
                "project__pi__username",
                "project__pi__first_name",
                "project__pi__last_name",
                "project__pi__email",
            )
            .annotate(
                is_project_pi=ExpressionWrapper(
                    Q(user=F("project__pi")),
                    output_field=BooleanField(),
                ),
                is_project_manager=ExpressionWrapper(
                    Q(role__name="Manager"),
                    output_field=BooleanField(),
                ),
            )
            .order_by(
                "-is_project_pi",
                "-is_project_manager",
                Lower("project__pi__username").asc(),
                Lower("project__title").asc(),
                # unlikely things will get to this point unless there's almost-duplicate projects
                "-project__pk",  # more performant stand-in for '-project__created'
            )
            .prefetch_related(
                Prefetch(
                    lookup="project__projectuser_set",
                    queryset=ProjectUser.objects.filter(
                        role__name="Manager",
                        status__name__in=ongoing_projectuser_statuses,
                    )
                    .exclude(
                        user__pk__in=[
                            F(
                                "project__pi__pk"
                            ),  # we assume pi is 'Manager' or can act like one - no need to list twice
                            viewed_user.pk,  # we display elsewhere if the user is a manager of this project
                        ],
                    )
                    .select_related(
                        "status",
                        "user",
                    )
                    .only(
                        "status__name",
                        "user__username",
                        "user__first_name",
                        "user__last_name",
                        "user__email",
                    )
                    .order_by(
                        "user__username",
                    ),
                    to_attr="project_managers",
                ),
            )
        )

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["viewed_user"] = self.viewed_user

        if self.request.user == self.viewed_user:
            context["user_pronounish"] = "You"
            context["user_verbform_be"] = "are"
        else:
            context["user_pronounish"] = "This user"
            context["user_verbform_be"] = "is"

        return context


class UserUpgradeAccount(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return True

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_superuser:
            messages.error(request, "You are already a super user")
            return HttpResponseRedirect(reverse("user-profile"))

        if request.user.userprofile.is_pi:
            messages.error(request, "Your account has already been upgraded")
            return HttpResponseRedirect(reverse("user-profile"))

        return super().dispatch(request, *args, **kwargs)

    def post(self, request):
        if EMAIL_ENABLED:
            send_email_template(
                "Upgrade Account Request",
                "email/upgrade_account_request.txt",
                {"user": request.user},
                EMAIL_SENDER,
                [EMAIL_TICKET_SYSTEM_ADDRESS],
            )

        messages.success(request, "Your request has been sent")
        return HttpResponseRedirect(reverse("user-profile"))


class UserSearchHome(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "user/user_search_home.html"

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context["user_search_form"] = UserSearchForm()
        return context

    def test_func(self):
        return self.request.user.is_staff


class UserSearchResults(LoginRequiredMixin, UserPassesTestMixin, View):
    template_name = "user/user_search_results.html"
    raise_exception = True

    def post(self, request):
        user_search_string = request.POST.get("q")

        search_by = request.POST.get("search_by")

        cobmined_user_search_obj = CombinedUserSearch(user_search_string, search_by)
        context = cobmined_user_search_obj.search()

        return render(request, self.template_name, context)

    def test_func(self):
        return self.request.user.is_staff


class UserListAllocations(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "user/user_list_allocations.html"

    def test_func(self):
        return self.request.user.is_superuser or self.request.user.userprofile.is_pi

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)

        user_dict = {}

        for project in Project.objects.filter(pi=self.request.user):
            for allocation in project.allocation_set.filter(status__name="Active"):
                for allocation_user in allocation.allocationuser_set.filter(status__name="Active").order_by(
                    "user__username"
                ):
                    if allocation_user.user not in user_dict:
                        user_dict[allocation_user.user] = []

                    user_dict[allocation_user.user].append(allocation)

        context["user_dict"] = user_dict

        return context
