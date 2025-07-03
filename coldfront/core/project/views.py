# SPDX-FileCopyrightText: (C) ColdFront Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

import datetime
import logging

from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.models import User
from django.contrib.messages.views import SuccessMessageMixin
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import Q
from django.forms import formset_factory
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, UpdateView
from django.views.generic.base import TemplateView
from django.views.generic.edit import FormView

from coldfront.config.core import ALLOCATION_EULA_ENABLE
from coldfront.core.allocation.models import (
    Allocation,
    AllocationStatusChoice,
    AllocationUser,
    AllocationUserStatusChoice,
)
from coldfront.core.allocation.signals import allocation_activate_user, allocation_remove_user
from coldfront.core.allocation.utils import generate_guauge_data_from_usage
from coldfront.core.grant.models import Grant
from coldfront.core.project.forms import (
    ProjectAddUserForm,
    ProjectAddUsersToAllocationForm,
    ProjectAttributeAddForm,
    ProjectAttributeDeleteForm,
    ProjectAttributeUpdateForm,
    ProjectCreationForm,
    ProjectRemoveUserForm,
    ProjectReviewEmailForm,
    ProjectReviewForm,
    ProjectSearchForm,
    ProjectUserUpdateForm,
)
from coldfront.core.project.models import (
    Project,
    ProjectAttribute,
    ProjectReview,
    ProjectReviewStatusChoice,
    ProjectStatusChoice,
    ProjectUser,
    ProjectUserMessage,
    ProjectUserRoleChoice,
    ProjectUserStatusChoice,
)
from coldfront.core.project.signals import (
    project_activate_user,
    project_archive,
    project_new,
    project_remove_user,
    project_update,
)
from coldfront.core.project.utils import determine_automated_institution_choice, generate_project_code
from coldfront.core.publication.models import Publication
from coldfront.core.research_output.models import ResearchOutput
from coldfront.core.user.forms import UserSearchForm
from coldfront.core.user.utils import CombinedUserSearch
from coldfront.core.utils.common import get_domain_url, import_from_settings
from coldfront.core.utils.mail import send_email, send_email_template

EMAIL_ENABLED = import_from_settings("EMAIL_ENABLED", False)
ALLOCATION_ENABLE_ALLOCATION_RENEWAL = import_from_settings("ALLOCATION_ENABLE_ALLOCATION_RENEWAL", True)
ALLOCATION_DEFAULT_ALLOCATION_LENGTH = import_from_settings("ALLOCATION_DEFAULT_ALLOCATION_LENGTH", 365)

if EMAIL_ENABLED:
    EMAIL_DIRECTOR_EMAIL_ADDRESS = import_from_settings("EMAIL_DIRECTOR_EMAIL_ADDRESS")
    EMAIL_SENDER = import_from_settings("EMAIL_SENDER")

PROJECT_CODE = import_from_settings("PROJECT_CODE", False)
PROJECT_CODE_PADDING = import_from_settings("PROJECT_CODE_PADDING", False)

logger = logging.getLogger(__name__)
PROJECT_INSTITUTION_EMAIL_MAP = import_from_settings("PROJECT_INSTITUTION_EMAIL_MAP", False)


class ProjectDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = Project
    template_name = "project/project_detail.html"
    context_object_name = "project"

    def test_func(self):
        """UserPassesTestMixin Tests"""
        if self.request.user.is_superuser:
            return True

        if self.request.user.has_perm("project.can_view_all_projects"):
            return True

        project_obj = self.get_object()

        if project_obj.projectuser_set.filter(user=self.request.user, status__name="Active").exists():
            return True

        messages.error(self.request, "You do not have permission to view the previous page.")
        return False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Can the user update the project?
        if self.request.user.is_superuser:
            context["is_allowed_to_update_project"] = True
        elif self.object.projectuser_set.filter(user=self.request.user).exists():
            project_user = self.object.projectuser_set.get(user=self.request.user)
            if project_user.role.name == "Manager":
                context["is_allowed_to_update_project"] = True
            else:
                context["is_allowed_to_update_project"] = False
        else:
            context["is_allowed_to_update_project"] = False

        pk = self.kwargs.get("pk")
        project_obj = get_object_or_404(Project, pk=pk)

        if self.request.user.is_superuser:
            attributes_with_usage = [
                attribute
                for attribute in project_obj.projectattribute_set.all().order_by("proj_attr_type__name")
                if hasattr(attribute, "projectattributeusage")
            ]

            attributes = [
                attribute for attribute in project_obj.projectattribute_set.all().order_by("proj_attr_type__name")
            ]

        else:
            attributes_with_usage = [
                attribute
                for attribute in project_obj.projectattribute_set.filter(proj_attr_type__is_private=False)
                if hasattr(attribute, "projectattributeusage")
            ]

            attributes = [
                attribute for attribute in project_obj.projectattribute_set.filter(proj_attr_type__is_private=False)
            ]

        guage_data = []
        invalid_attributes = []
        for attribute in attributes_with_usage:
            try:
                guage_data.append(
                    generate_guauge_data_from_usage(
                        attribute.proj_attr_type.name,
                        float(attribute.value),
                        float(attribute.projectattributeusage.value),
                    )
                )
            except ValueError:
                logger.error(
                    "Allocation attribute '%s' is not an int but has a usage", attribute.allocation_attribute_type.name
                )
                invalid_attributes.append(attribute)

        for a in invalid_attributes:
            attributes_with_usage.remove(a)

        # Only show 'Active Users'
        project_users = self.object.projectuser_set.filter(status__name="Active").order_by("user__username")

        context["mailto"] = "mailto:" + ",".join([user.user.email for user in project_users])

        if self.request.user.is_superuser or self.request.user.has_perm("allocation.can_view_all_allocations"):
            allocations = (
                Allocation.objects.prefetch_related("resources").filter(project=self.object).order_by("-end_date")
            )
        else:
            if self.object.status.name in [
                "Active",
                "New",
            ]:
                allocations = (
                    Allocation.objects.filter(
                        Q(project=self.object)
                        & Q(project__projectuser__user=self.request.user)
                        & Q(
                            project__projectuser__status__name__in=[
                                "Active",
                            ]
                        )
                        & Q(allocationuser__user=self.request.user)
                        & Q(allocationuser__status__name__in=["Active", "PendingEULA"])
                    )
                    .distinct()
                    .order_by("-end_date")
                )
            else:
                allocations = Allocation.objects.prefetch_related("resources").filter(project=self.object)

        user_status = []
        for allocation in allocations:
            if allocation.allocationuser_set.filter(user=self.request.user).exists():
                user_status.append(allocation.allocationuser_set.get(user=self.request.user).status.name)

        context["publications"] = Publication.objects.filter(project=self.object, status="Active").order_by("-year")
        context["research_outputs"] = ResearchOutput.objects.filter(project=self.object).order_by("-created")
        context["grants"] = Grant.objects.filter(
            project=self.object, status__name__in=["Active", "Pending", "Archived"]
        )
        context["allocations"] = allocations
        context["user_allocation_status"] = user_status
        context["attributes"] = attributes
        context["guage_data"] = guage_data
        context["attributes_with_usage"] = attributes_with_usage
        context["project_users"] = project_users
        context["ALLOCATION_ENABLE_ALLOCATION_RENEWAL"] = ALLOCATION_ENABLE_ALLOCATION_RENEWAL
        context["PROJECT_INSTITUTION_EMAIL_MAP"] = PROJECT_INSTITUTION_EMAIL_MAP

        try:
            context["ondemand_url"] = settings.ONDEMAND_URL
        except AttributeError:
            pass

        return context


class ProjectListView(LoginRequiredMixin, ListView):
    model = Project
    template_name = "project/project_list.html"
    prefetch_related = [
        "pi",
        "status",
        "field_of_science",
    ]
    context_object_name = "project_list"
    paginate_by = 25

    def get_queryset(self):
        order_by = self.request.GET.get("order_by", "id")
        direction = self.request.GET.get("direction", "asc")
        if order_by != "name":
            if direction == "asc":
                direction = ""
            if direction == "des":
                direction = "-"
            order_by = direction + order_by

        project_search_form = ProjectSearchForm(self.request.GET)

        if project_search_form.is_valid():
            data = project_search_form.cleaned_data
            if data.get("show_all_projects") and (
                self.request.user.is_superuser or self.request.user.has_perm("project.can_view_all_projects")
            ):
                projects = (
                    Project.objects.prefetch_related(
                        "pi",
                        "field_of_science",
                        "status",
                    )
                    .filter(
                        status__name__in=[
                            "New",
                            "Active",
                        ]
                    )
                    .order_by(order_by)
                )
            else:
                projects = (
                    Project.objects.prefetch_related(
                        "pi",
                        "field_of_science",
                        "status",
                    )
                    .filter(
                        Q(
                            status__name__in=[
                                "New",
                                "Active",
                            ]
                        )
                        & Q(projectuser__user=self.request.user)
                        & Q(projectuser__status__name="Active")
                    )
                    .order_by(order_by)
                )

            # Last Name
            if data.get("last_name"):
                projects = projects.filter(pi__last_name__icontains=data.get("last_name"))

            # Username
            if data.get("username"):
                projects = projects.filter(
                    Q(pi__username__icontains=data.get("username"))
                    | Q(projectuser__user__username__icontains=data.get("username"))
                    & Q(projectuser__status__name="Active")
                )

            # Field of Science
            if data.get("field_of_science"):
                projects = projects.filter(field_of_science__description__icontains=data.get("field_of_science"))

        else:
            projects = (
                Project.objects.prefetch_related(
                    "pi",
                    "field_of_science",
                    "status",
                )
                .filter(
                    Q(
                        status__name__in=[
                            "New",
                            "Active",
                        ]
                    )
                    & Q(projectuser__user=self.request.user)
                    & Q(projectuser__status__name="Active")
                )
                .order_by(order_by)
            )

        return projects.distinct()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        projects_count = self.get_queryset().count()
        context["projects_count"] = projects_count

        project_search_form = ProjectSearchForm(self.request.GET)
        if project_search_form.is_valid():
            context["project_search_form"] = project_search_form
            data = project_search_form.cleaned_data
            filter_parameters = ""
            for key, value in data.items():
                if value:
                    if isinstance(value, list):
                        for ele in value:
                            filter_parameters += "{}={}&".format(key, ele)
                    else:
                        filter_parameters += "{}={}&".format(key, value)
            context["project_search_form"] = project_search_form
        else:
            filter_parameters = None
            context["project_search_form"] = ProjectSearchForm()

        order_by = self.request.GET.get("order_by")
        if order_by:
            direction = self.request.GET.get("direction")
            filter_parameters_with_order_by = filter_parameters + "order_by=%s&direction=%s&" % (order_by, direction)
        else:
            filter_parameters_with_order_by = filter_parameters

        if filter_parameters:
            context["expand_accordion"] = "show"

        context["filter_parameters"] = filter_parameters
        context["filter_parameters_with_order_by"] = filter_parameters_with_order_by
        context["PROJECT_INSTITUTION_EMAIL_MAP"] = PROJECT_INSTITUTION_EMAIL_MAP

        project_list = context.get("project_list")
        paginator = Paginator(project_list, self.paginate_by)

        page = self.request.GET.get("page")

        try:
            project_list = paginator.page(page)
        except PageNotAnInteger:
            project_list = paginator.page(1)
        except EmptyPage:
            project_list = paginator.page(paginator.num_pages)

        return context


class ProjectArchivedListView(LoginRequiredMixin, ListView):
    model = Project
    template_name = "project/project_archived_list.html"
    prefetch_related = [
        "pi",
        "status",
        "field_of_science",
    ]
    context_object_name = "project_list"
    paginate_by = 10

    def get_queryset(self):
        order_by = self.request.GET.get("order_by", "id")
        direction = self.request.GET.get("direction", "")
        if order_by != "name":
            if direction == "des":
                direction = "-"
            order_by = direction + order_by

        project_search_form = ProjectSearchForm(self.request.GET)

        if project_search_form.is_valid():
            data = project_search_form.cleaned_data
            if data.get("show_all_projects") and (
                self.request.user.is_superuser or self.request.user.has_perm("project.can_view_all_projects")
            ):
                projects = (
                    Project.objects.prefetch_related(
                        "pi",
                        "field_of_science",
                        "status",
                    )
                    .filter(
                        status__name__in=[
                            "Archived",
                        ]
                    )
                    .order_by(order_by)
                )
            else:
                projects = (
                    Project.objects.prefetch_related(
                        "pi",
                        "field_of_science",
                        "status",
                    )
                    .filter(
                        Q(
                            status__name__in=[
                                "Archived",
                            ]
                        )
                        & Q(projectuser__user=self.request.user)
                        & Q(projectuser__status__name="Active")
                    )
                    .order_by(order_by)
                )

            # Last Name
            if data.get("last_name"):
                projects = projects.filter(pi__last_name__icontains=data.get("last_name"))

            # Username
            if data.get("username"):
                projects = projects.filter(pi__username__icontains=data.get("username"))

            # Field of Science
            if data.get("field_of_science"):
                projects = projects.filter(field_of_science__description__icontains=data.get("field_of_science"))

        else:
            projects = (
                Project.objects.prefetch_related(
                    "pi",
                    "field_of_science",
                    "status",
                )
                .filter(
                    Q(
                        status__name__in=[
                            "Archived",
                        ]
                    )
                    & Q(projectuser__user=self.request.user)
                    & Q(projectuser__status__name="Active")
                )
                .order_by(order_by)
            )

        return projects

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        projects_count = self.get_queryset().count()
        context["projects_count"] = projects_count
        context["expand"] = False

        project_search_form = ProjectSearchForm(self.request.GET)
        if project_search_form.is_valid():
            context["project_search_form"] = project_search_form
            data = project_search_form.cleaned_data
            filter_parameters = ""
            for key, value in data.items():
                if value:
                    if isinstance(value, list):
                        for ele in value:
                            filter_parameters += "{}={}&".format(key, ele)
                    else:
                        filter_parameters += "{}={}&".format(key, value)
            context["project_search_form"] = project_search_form
        else:
            filter_parameters = None
            context["project_search_form"] = ProjectSearchForm()

        order_by = self.request.GET.get("order_by")
        if order_by:
            direction = self.request.GET.get("direction")
            filter_parameters_with_order_by = filter_parameters + "order_by=%s&direction=%s&" % (order_by, direction)
        else:
            filter_parameters_with_order_by = filter_parameters

        if filter_parameters:
            context["expand_accordion"] = "show"

        context["filter_parameters"] = filter_parameters
        context["filter_parameters_with_order_by"] = filter_parameters_with_order_by

        project_list = context.get("project_list")
        paginator = Paginator(project_list, self.paginate_by)

        page = self.request.GET.get("page")

        try:
            project_list = paginator.page(page)
        except PageNotAnInteger:
            project_list = paginator.page(1)
        except EmptyPage:
            project_list = paginator.page(paginator.num_pages)

        return context


class ProjectArchiveProjectView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "project/project_archive.html"

    def test_func(self):
        """UserPassesTestMixin Tests"""
        if self.request.user.is_superuser:
            return True

        project_obj = get_object_or_404(Project, pk=self.kwargs.get("pk"))

        if project_obj.pi == self.request.user:
            return True

        if project_obj.projectuser_set.filter(
            user=self.request.user, role__name="Manager", status__name="Active"
        ).exists():
            return True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pk = self.kwargs.get("pk")
        project = get_object_or_404(Project, pk=pk)

        context["project"] = project

        return context

    def post(self, request, *args, **kwargs):
        pk = self.kwargs.get("pk")
        project = get_object_or_404(Project, pk=pk)
        project_status_archive = ProjectStatusChoice.objects.get(name="Archived")
        allocation_status_expired = AllocationStatusChoice.objects.get(name="Expired")
        end_date = datetime.datetime.now()
        project.status = project_status_archive
        project.save()

        # project signals
        project_archive.send(sender=self.__class__, project_obj=project)

        for allocation in project.allocation_set.filter(status__name="Active"):
            allocation.status = allocation_status_expired
            allocation.end_date = end_date
            allocation.save()
        return redirect(reverse("project-detail", kwargs={"pk": project.pk}))


class ProjectCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = Project
    template_name_suffix = "_create_form"
    form_class = ProjectCreationForm

    def test_func(self):
        """UserPassesTestMixin Tests"""
        if self.request.user.is_superuser:
            return True

        if self.request.user.userprofile.is_pi:
            return True

    def form_valid(self, form):
        project_obj = form.save(commit=False)
        form.instance.pi = self.request.user
        form.instance.status = ProjectStatusChoice.objects.get(name="New")
        project_obj.save()
        self.object = project_obj

        ProjectUser.objects.create(
            user=self.request.user,
            project=project_obj,
            role=ProjectUserRoleChoice.objects.get(name="Manager"),
            status=ProjectUserStatusChoice.objects.get(name="Active"),
        )

        if PROJECT_CODE:
            """
            Set the ProjectCode object, if PROJECT_CODE is defined. 
            If PROJECT_CODE_PADDING is defined, the set amount of padding will be added to PROJECT_CODE.
            """
            project_obj.project_code = generate_project_code(PROJECT_CODE, project_obj.pk, PROJECT_CODE_PADDING or 0)
            project_obj.save(update_fields=["project_code"])

        if PROJECT_INSTITUTION_EMAIL_MAP:
            determine_automated_institution_choice(project_obj, PROJECT_INSTITUTION_EMAIL_MAP)

        # project signals
        project_new.send(sender=self.__class__, project_obj=project_obj)

        return super().form_valid(form)

    def get_success_url(self):
        return reverse("project-detail", kwargs={"pk": self.object.pk})


class ProjectUpdateView(SuccessMessageMixin, LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Project
    template_name_suffix = "_update_form"
    fields = [
        "title",
        "description",
        "field_of_science",
    ]
    success_message = "Project updated."

    def test_func(self):
        """UserPassesTestMixin Tests"""
        if self.request.user.is_superuser:
            return True

        project_obj = self.get_object()

        if project_obj.pi == self.request.user:
            return True

        if project_obj.projectuser_set.filter(
            user=self.request.user, role__name="Manager", status__name="Active"
        ).exists():
            return True

    def dispatch(self, request, *args, **kwargs):
        project_obj = get_object_or_404(Project, pk=self.kwargs.get("pk"))

        if PROJECT_CODE and project_obj.project_code == "":
            """
            Updates project code if no value was set, providing the feature is activated. 
            """
            project_obj.project_code = generate_project_code(PROJECT_CODE, project_obj.pk, PROJECT_CODE_PADDING or 0)
            project_obj.save(update_fields=["project_code"])

        if project_obj.status.name not in [
            "Active",
            "New",
        ]:
            messages.error(request, "You cannot update an archived project.")
            return HttpResponseRedirect(reverse("project-detail", kwargs={"pk": project_obj.pk}))
        else:
            return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        # project signals
        project_update.send(sender=self.__class__, project_obj=self.object)
        return reverse("project-detail", kwargs={"pk": self.object.pk})


class ProjectAddUsersSearchView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "project/project_add_users.html"

    def test_func(self):
        """UserPassesTestMixin Tests"""
        if self.request.user.is_superuser:
            return True

        project_obj = get_object_or_404(Project, pk=self.kwargs.get("pk"))

        if project_obj.pi == self.request.user:
            return True

        if project_obj.projectuser_set.filter(
            user=self.request.user, role__name="Manager", status__name="Active"
        ).exists():
            return True

    def dispatch(self, request, *args, **kwargs):
        project_obj = get_object_or_404(Project, pk=self.kwargs.get("pk"))
        if project_obj.status.name not in [
            "Active",
            "New",
        ]:
            messages.error(request, "You cannot add users to an archived project.")
            return HttpResponseRedirect(reverse("project-detail", kwargs={"pk": project_obj.pk}))
        else:
            return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context["user_search_form"] = UserSearchForm()
        context["project"] = Project.objects.get(pk=self.kwargs.get("pk"))
        return context


class ProjectAddUsersSearchResultsView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "project/add_user_search_results.html"
    raise_exception = True

    def test_func(self):
        """UserPassesTestMixin Tests"""
        if self.request.user.is_superuser:
            return True

        project_obj = get_object_or_404(Project, pk=self.kwargs.get("pk"))

        if project_obj.pi == self.request.user:
            return True

        if project_obj.projectuser_set.filter(
            user=self.request.user, role__name="Manager", status__name="Active"
        ).exists():
            return True

    def dispatch(self, request, *args, **kwargs):
        project_obj = get_object_or_404(Project, pk=self.kwargs.get("pk"))
        if project_obj.status.name not in [
            "Active",
            "New",
        ]:
            messages.error(request, "You cannot add users to an archived project.")
            return HttpResponseRedirect(reverse("project-detail", kwargs={"pk": project_obj.pk}))
        else:
            return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        user_search_string = request.POST.get("q")
        search_by = request.POST.get("search_by")
        pk = self.kwargs.get("pk")

        project_obj = get_object_or_404(Project, pk=pk)

        users_to_exclude = [ele.user.username for ele in project_obj.projectuser_set.filter(status__name="Active")]

        cobmined_user_search_obj = CombinedUserSearch(user_search_string, search_by, users_to_exclude)

        context = cobmined_user_search_obj.search()

        matches = context.get("matches")
        for match in matches:
            match.update({"role": ProjectUserRoleChoice.objects.get(name="User")})

        if matches:
            formset = formset_factory(ProjectAddUserForm, max_num=len(matches))
            formset = formset(initial=matches, prefix="userform")
            context["formset"] = formset
            context["user_search_string"] = user_search_string
            context["search_by"] = search_by

        if len(user_search_string.split()) > 1:
            users_already_in_project = []
            for ele in user_search_string.split():
                if ele in users_to_exclude:
                    users_already_in_project.append(ele)
            context["users_already_in_project"] = users_already_in_project

        # The following block of code is used to hide/show the allocation div in the form.
        if project_obj.allocation_set.filter(status__name__in=["Active", "New", "Renewal Requested"]).exists():
            div_allocation_class = "placeholder_div_class"
        else:
            div_allocation_class = "d-none"
        context["div_allocation_class"] = div_allocation_class
        ###

        allocation_form = ProjectAddUsersToAllocationForm(request.user, project_obj.pk, prefix="allocationform")
        context["pk"] = pk
        context["allocation_form"] = allocation_form
        return render(request, self.template_name, context)


class ProjectAddUsersView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        """UserPassesTestMixin Tests"""
        if self.request.user.is_superuser:
            return True

        project_obj = get_object_or_404(Project, pk=self.kwargs.get("pk"))

        if project_obj.pi == self.request.user:
            return True

        if project_obj.projectuser_set.filter(
            user=self.request.user, role__name="Manager", status__name="Active"
        ).exists():
            return True

    def dispatch(self, request, *args, **kwargs):
        project_obj = get_object_or_404(Project, pk=self.kwargs.get("pk"))
        if project_obj.status.name not in [
            "Active",
            "New",
        ]:
            messages.error(request, "You cannot add users to an archived project.")
            return HttpResponseRedirect(reverse("project-detail", kwargs={"pk": project_obj.pk}))
        else:
            return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        user_search_string = request.POST.get("q")
        search_by = request.POST.get("search_by")
        pk = self.kwargs.get("pk")

        project_obj = get_object_or_404(Project, pk=pk)

        users_to_exclude = [ele.user.username for ele in project_obj.projectuser_set.filter(status__name="Active")]

        cobmined_user_search_obj = CombinedUserSearch(user_search_string, search_by, users_to_exclude)

        context = cobmined_user_search_obj.search()

        matches = context.get("matches")
        for match in matches:
            match.update({"role": ProjectUserRoleChoice.objects.get(name="User")})

        formset = formset_factory(ProjectAddUserForm, max_num=len(matches))
        formset = formset(request.POST, initial=matches, prefix="userform")

        allocation_form = ProjectAddUsersToAllocationForm(
            request.user, project_obj.pk, request.POST, prefix="allocationform"
        )

        added_users_count = 0
        if formset.is_valid() and allocation_form.is_valid():
            project_user_active_status_choice = ProjectUserStatusChoice.objects.get(name="Active")
            allocation_user_active_status_choice = AllocationUserStatusChoice.objects.get(name="Active")
            if ALLOCATION_EULA_ENABLE:
                allocation_user_pending_status_choice = AllocationUserStatusChoice.objects.get(name="PendingEULA")

            allocation_form_data = allocation_form.cleaned_data["allocation"]
            if "__select_all__" in allocation_form_data:
                allocation_form_data.remove("__select_all__")
            for form in formset:
                user_form_data = form.cleaned_data
                if user_form_data["selected"]:
                    added_users_count += 1

                    # Will create local copy of user if not already present in local database
                    user_obj, _ = User.objects.get_or_create(username=user_form_data.get("username"))
                    user_obj.first_name = user_form_data.get("first_name")
                    user_obj.last_name = user_form_data.get("last_name")
                    user_obj.email = user_form_data.get("email")
                    user_obj.save()

                    role_choice = user_form_data.get("role")
                    # Is the user already in the project?
                    if project_obj.projectuser_set.filter(user=user_obj).exists():
                        project_user_obj = project_obj.projectuser_set.get(user=user_obj)
                        project_user_obj.role = role_choice
                        project_user_obj.status = project_user_active_status_choice
                        project_user_obj.save()
                    else:
                        project_user_obj = ProjectUser.objects.create(
                            user=user_obj,
                            project=project_obj,
                            role=role_choice,
                            status=project_user_active_status_choice,
                        )

                    # project signals
                    project_activate_user.send(sender=self.__class__, project_user_pk=project_user_obj.pk)

                    for allocation in Allocation.objects.filter(pk__in=allocation_form_data):
                        has_eula = allocation.get_eula()
                        user_status_choice = allocation_user_active_status_choice
                        if allocation.allocationuser_set.filter(user=user_obj).exists():
                            allocation_user_obj = allocation.allocationuser_set.get(user=user_obj)
                            if (
                                ALLOCATION_EULA_ENABLE
                                and has_eula
                                and (allocation_user_obj.status != allocation_user_active_status_choice)
                            ):
                                user_status_choice = allocation_user_pending_status_choice
                            allocation_user_obj.status = user_status_choice
                            allocation_user_obj.save()
                        else:
                            if ALLOCATION_EULA_ENABLE and has_eula:
                                user_status_choice = allocation_user_pending_status_choice
                            allocation_user_obj = AllocationUser.objects.create(
                                allocation=allocation, user=user_obj, status=user_status_choice
                            )
                        if user_status_choice == allocation_user_active_status_choice:
                            allocation_activate_user.send(
                                sender=self.__class__, allocation_user_pk=allocation_user_obj.pk
                            )

            messages.success(request, "Added {} users to project.".format(added_users_count))
        else:
            if not formset.is_valid():
                for error in formset.errors:
                    messages.error(request, error)

            if not allocation_form.is_valid():
                for error in allocation_form.errors:
                    messages.error(request, error)

        return HttpResponseRedirect(reverse("project-detail", kwargs={"pk": pk}))


class ProjectRemoveUsersView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "project/project_remove_users.html"

    def test_func(self):
        """UserPassesTestMixin Tests"""
        if self.request.user.is_superuser:
            return True

        project_obj = get_object_or_404(Project, pk=self.kwargs.get("pk"))

        if project_obj.pi == self.request.user:
            return True

        if project_obj.projectuser_set.filter(
            user=self.request.user, role__name="Manager", status__name="Active"
        ).exists():
            return True

    def dispatch(self, request, *args, **kwargs):
        project_obj = get_object_or_404(Project, pk=self.kwargs.get("pk"))
        if project_obj.status.name not in [
            "Active",
            "New",
        ]:
            messages.error(request, "You cannot remove users from an archived project.")
            return HttpResponseRedirect(reverse("project-detail", kwargs={"pk": project_obj.pk}))
        else:
            return super().dispatch(request, *args, **kwargs)

    def get_users_to_remove(self, project_obj):
        users_to_remove = [
            {
                "username": ele.user.username,
                "first_name": ele.user.first_name,
                "last_name": ele.user.last_name,
                "email": ele.user.email,
                "role": ele.role,
            }
            for ele in project_obj.projectuser_set.filter(status__name="Active").order_by("user__username")
            if ele.user != self.request.user and ele.user != project_obj.pi
        ]

        return users_to_remove

    def get(self, request, *args, **kwargs):
        pk = self.kwargs.get("pk")
        project_obj = get_object_or_404(Project, pk=pk)

        users_to_remove = self.get_users_to_remove(project_obj)
        context = {}

        if users_to_remove:
            formset = formset_factory(ProjectRemoveUserForm, max_num=len(users_to_remove))
            formset = formset(initial=users_to_remove, prefix="userform")
            context["formset"] = formset

        context["project"] = get_object_or_404(Project, pk=pk)
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        pk = self.kwargs.get("pk")
        project_obj = get_object_or_404(Project, pk=pk)

        users_to_remove = self.get_users_to_remove(project_obj)

        formset = formset_factory(ProjectRemoveUserForm, max_num=len(users_to_remove))
        formset = formset(request.POST, initial=users_to_remove, prefix="userform")

        remove_users_count = 0

        if formset.is_valid():
            project_user_removed_status_choice = ProjectUserStatusChoice.objects.get(name="Removed")
            allocation_user_removed_status_choice = AllocationUserStatusChoice.objects.get(name="Removed")
            for form in formset:
                user_form_data = form.cleaned_data
                if user_form_data["selected"]:
                    remove_users_count += 1

                    user_obj = User.objects.get(username=user_form_data.get("username"))

                    if project_obj.pi == user_obj:
                        continue

                    project_user_obj = project_obj.projectuser_set.get(user=user_obj)
                    project_user_obj.status = project_user_removed_status_choice
                    project_user_obj.save()

                    # project signals
                    project_remove_user.send(sender=self.__class__, project_user_pk=project_user_obj.pk)

                    # get allocation to remove users from
                    allocations_to_remove_user_from = project_obj.allocation_set.filter(
                        status__name__in=["Active", "New", "Renewal Requested"]
                    )
                    for allocation in allocations_to_remove_user_from:
                        for allocation_user_obj in allocation.allocationuser_set.filter(
                            user=user_obj,
                            status__name__in=[
                                "Active",
                            ],
                        ):
                            allocation_user_obj.status = allocation_user_removed_status_choice
                            allocation_user_obj.save()

                            allocation_remove_user.send(
                                sender=self.__class__, allocation_user_pk=allocation_user_obj.pk
                            )

            if remove_users_count == 1:
                messages.success(request, "Removed {} user from project.".format(remove_users_count))
            else:
                messages.success(request, "Removed {} users from project.".format(remove_users_count))
        else:
            for error in formset.errors:
                messages.error(request, error)

        return HttpResponseRedirect(reverse("project-detail", kwargs={"pk": pk}))


class ProjectUserDetail(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "project/project_user_detail.html"

    def test_func(self):
        """UserPassesTestMixin Tests"""
        if self.request.user.is_superuser:
            return True

        project_obj = get_object_or_404(Project, pk=self.kwargs.get("pk"))

        if project_obj.pi == self.request.user:
            return True

        if project_obj.projectuser_set.filter(
            user=self.request.user, role__name="Manager", status__name="Active"
        ).exists():
            return True

    def get(self, request, *args, **kwargs):
        project_obj = get_object_or_404(Project, pk=self.kwargs.get("pk"))
        project_user_pk = self.kwargs.get("project_user_pk")

        if project_obj.projectuser_set.filter(pk=project_user_pk).exists():
            project_user_obj = project_obj.projectuser_set.get(pk=project_user_pk)

            project_user_update_form = ProjectUserUpdateForm(
                initial={"role": project_user_obj.role, "enable_notifications": project_user_obj.enable_notifications}
            )

            context = {}
            context["project_obj"] = project_obj
            context["project_user_update_form"] = project_user_update_form
            context["project_user_obj"] = project_user_obj

            return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        project_obj = get_object_or_404(Project, pk=self.kwargs.get("pk"))
        project_user_pk = self.kwargs.get("project_user_pk")

        if project_obj.status.name not in [
            "Active",
            "New",
        ]:
            messages.error(request, "You cannot update a user in an archived project.")
            return HttpResponseRedirect(reverse("project-user-detail", kwargs={"pk": project_user_pk}))

        if project_obj.projectuser_set.filter(id=project_user_pk).exists():
            project_user_obj = project_obj.projectuser_set.get(pk=project_user_pk)

            if project_user_obj.user == project_user_obj.project.pi:
                messages.error(request, "PI role and email notification option cannot be changed.")
                return HttpResponseRedirect(reverse("project-user-detail", kwargs={"pk": project_user_pk}))

            project_user_update_form = ProjectUserUpdateForm(
                request.POST,
                initial={
                    "role": project_user_obj.role.name,
                    "enable_notifications": project_user_obj.enable_notifications,
                },
            )

            if project_user_update_form.is_valid():
                form_data = project_user_update_form.cleaned_data
                project_user_obj.role = ProjectUserRoleChoice.objects.get(name=form_data.get("role"))

                if project_user_obj.role.name == "Manager":
                    project_user_obj.enable_notifications = True
                else:
                    project_user_obj.enable_notifications = form_data.get("enable_notifications")
                project_user_obj.save()

                messages.success(request, "User details updated.")
                return HttpResponseRedirect(
                    reverse(
                        "project-user-detail", kwargs={"pk": project_obj.pk, "project_user_pk": project_user_obj.pk}
                    )
                )


@login_required
def project_update_email_notification(request):
    if request.method == "POST":
        data = request.POST
        project_user_obj = get_object_or_404(ProjectUser, pk=data.get("user_project_id"))

        project_obj = project_user_obj.project

        allowed = False
        if project_obj.pi == request.user:
            allowed = True

        if project_obj.projectuser_set.filter(user=request.user, role__name="Manager", status__name="Active").exists():
            allowed = True

        if project_user_obj.user == request.user:
            allowed = True

        if request.user.is_superuser:
            allowed = True

        if allowed is False:
            return HttpResponse("not allowed", status=403)
        else:
            checked = data.get("checked")
            if checked == "true":
                project_user_obj.enable_notifications = True
                project_user_obj.save()
                return HttpResponse("checked", status=200)
            elif checked == "false":
                project_user_obj.enable_notifications = False
                project_user_obj.save()
                return HttpResponse("unchecked", status=200)
            else:
                return HttpResponse("no checked", status=400)
    else:
        return HttpResponse("no POST", status=400)


class ProjectReviewView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "project/project_review.html"
    login_url = "/"  # redirect URL if fail test_func

    def test_func(self):
        """UserPassesTestMixin Tests"""
        if self.request.user.is_superuser:
            return True

        project_obj = get_object_or_404(Project, pk=self.kwargs.get("pk"))

        if project_obj.pi == self.request.user:
            return True

        if project_obj.projectuser_set.filter(
            user=self.request.user, role__name="Manager", status__name="Active"
        ).exists():
            return True

        messages.error(self.request, "You do not have permissions to review this project.")

    def dispatch(self, request, *args, **kwargs):
        project_obj = get_object_or_404(Project, pk=self.kwargs.get("pk"))

        if not project_obj.needs_review:
            messages.error(request, "You do not need to review this project.")
            return HttpResponseRedirect(reverse("project-detail", kwargs={"pk": project_obj.pk}))

        if "Auto-Import Project".lower() in project_obj.title.lower():
            messages.error(
                request,
                'You must update the project title before reviewing your project. You cannot have "Auto-Import Project" in the title.',
            )
            return HttpResponseRedirect(reverse("project-update", kwargs={"pk": project_obj.pk}))

        if (
            "We do not have information about your research. Please provide a detailed description of your work and update your field of science. Thank you!"
            in project_obj.description
        ):
            messages.error(request, "You must update the project description before reviewing your project.")
            return HttpResponseRedirect(reverse("project-update", kwargs={"pk": project_obj.pk}))

        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        project_obj = get_object_or_404(Project, pk=self.kwargs.get("pk"))
        project_review_form = ProjectReviewForm(project_obj.pk)

        context = {}
        context["project"] = project_obj
        context["project_review_form"] = project_review_form
        context["project_users"] = ", ".join(
            [
                "{} {}".format(ele.user.first_name, ele.user.last_name)
                for ele in project_obj.projectuser_set.filter(status__name="Active").order_by("user__last_name")
            ]
        )

        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        project_obj = get_object_or_404(Project, pk=self.kwargs.get("pk"))
        project_review_form = ProjectReviewForm(project_obj.pk, request.POST)

        project_review_status_choice = ProjectReviewStatusChoice.objects.get(name="Pending")

        if project_review_form.is_valid():
            form_data = project_review_form.cleaned_data
            ProjectReview.objects.create(
                project=project_obj,
                reason_for_not_updating_project=form_data.get("reason"),
                status=project_review_status_choice,
            )

            project_obj.force_review = False
            project_obj.save()

            domain_url = get_domain_url(self.request)
            url = "{}{}".format(domain_url, reverse("project-review-list"))

            if EMAIL_ENABLED:
                send_email_template(
                    "New project review has been submitted",
                    "email/new_project_review.txt",
                    {"url": url},
                    EMAIL_SENDER,
                    [
                        EMAIL_DIRECTOR_EMAIL_ADDRESS,
                    ],
                )

            messages.success(request, "Project reviewed successfully.")
            return HttpResponseRedirect(reverse("project-detail", kwargs={"pk": project_obj.pk}))
        else:
            messages.error(request, "There was an error in processing  your project review.")
            return HttpResponseRedirect(reverse("project-detail", kwargs={"pk": project_obj.pk}))


class ProjectReviewListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = ProjectReview
    template_name = "project/project_review_list.html"
    prefetch_related = [
        "project",
    ]
    context_object_name = "project_review_list"

    def get_queryset(self):
        return ProjectReview.objects.filter(status__name="Pending")

    def test_func(self):
        """UserPassesTestMixin Tests"""

        if self.request.user.is_superuser:
            return True

        if self.request.user.has_perm("project.can_review_pending_project_reviews"):
            return True

        messages.error(self.request, "You do not have permission to review pending project reviews.")


class ProjectReviewCompleteView(LoginRequiredMixin, UserPassesTestMixin, View):
    login_url = "/"

    def test_func(self):
        """UserPassesTestMixin Tests"""

        if self.request.user.is_superuser:
            return True

        if self.request.user.has_perm("project.can_review_pending_project_reviews"):
            return True

        messages.error(self.request, "You do not have permission to mark a pending project review as completed.")

    def get(self, request, project_review_pk):
        project_review_obj = get_object_or_404(ProjectReview, pk=project_review_pk)

        project_review_status_completed_obj = ProjectReviewStatusChoice.objects.get(name="Completed")
        project_review_obj.status = project_review_status_completed_obj
        project_review_obj.project.project_needs_review = False
        project_review_obj.save()

        messages.success(request, "Project review for {} has been completed".format(project_review_obj.project.title))

        return HttpResponseRedirect(reverse("project-review-list"))


class ProjectReviewEmailView(LoginRequiredMixin, UserPassesTestMixin, FormView):
    form_class = ProjectReviewEmailForm
    template_name = "project/project_review_email.html"
    login_url = "/"

    def test_func(self):
        """UserPassesTestMixin Tests"""

        if self.request.user.is_superuser:
            return True

        if self.request.user.has_perm("project.can_review_pending_project_reviews"):
            return True

        messages.error(self.request, "You do not have permission to send email for a pending project review.")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pk = self.kwargs.get("pk")
        project_review_obj = get_object_or_404(ProjectReview, pk=pk)
        context["project_review"] = project_review_obj

        return context

    def get_form(self, form_class=None):
        """Return an instance of the form to be used in this view."""
        if form_class is None:
            form_class = self.get_form_class()
        return form_class(self.kwargs.get("pk"), **self.get_form_kwargs())

    def form_valid(self, form):
        pk = self.kwargs.get("pk")
        project_review_obj = get_object_or_404(ProjectReview, pk=pk)
        form_data = form.cleaned_data

        receiver_list = [project_review_obj.project.pi.email]
        cc = form_data.get("cc").strip()
        if cc:
            cc = cc.split(",")
        else:
            cc = []

        send_email(
            "Request for more information", form_data.get("email_body"), EMAIL_DIRECTOR_EMAIL_ADDRESS, receiver_list, cc
        )

        messages.success(
            self.request,
            "Email sent to {} {} ({})".format(
                project_review_obj.project.pi.first_name,
                project_review_obj.project.pi.last_name,
                project_review_obj.project.pi.username,
            ),
        )
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("project-review-list")


class ProjectNoteCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = ProjectUserMessage
    fields = "__all__"
    template_name = "project/project_note_create.html"

    def test_func(self):
        """UserPassesTestMixin Tests"""

        if self.request.user.is_superuser:
            return True
        else:
            messages.error(self.request, "You do not have permission to add allocation notes.")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pk = self.kwargs.get("pk")
        project_obj = get_object_or_404(Project, pk=pk)
        context["project"] = project_obj
        return context

    def get_initial(self):
        initial = super().get_initial()
        pk = self.kwargs.get("pk")
        project_obj = get_object_or_404(Project, pk=pk)
        author = self.request.user
        initial["project"] = project_obj
        initial["author"] = author
        return initial

    def get_form(self, form_class=None):
        """Return an instance of the form to be used in this view."""
        form = super().get_form(form_class)
        form.fields["project"].widget = forms.HiddenInput()
        form.fields["author"].widget = forms.HiddenInput()
        form.order_fields(["project", "author", "message", "is_private"])
        return form

    def get_success_url(self):
        return reverse("project-detail", kwargs={"pk": self.kwargs.get("pk")})


class ProjectAttributeCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = ProjectAttribute
    form_class = ProjectAttributeAddForm
    template_name = "project/project_attribute_create.html"

    def test_func(self):
        """UserPassesTestMixin Tests"""
        project_obj = get_object_or_404(Project, pk=self.kwargs.get("pk"))

        if self.request.user.is_superuser:
            return True

        if project_obj.pi == self.request.user:
            return True

        if project_obj.projectuser_set.filter(
            user=self.request.user, role__name="Manager", status__name="Active"
        ).exists():
            return True

        messages.error(self.request, "You do not have permission to add project attributes.")

    def get_initial(self):
        initial = super().get_initial()
        pk = self.kwargs.get("pk")
        initial["project"] = get_object_or_404(Project, pk=pk)
        initial["user"] = self.request.user
        return initial

    def get_form(self, form_class=None):
        """Return an instance of the form to be used in this view."""
        form = super().get_form(form_class)
        form.fields["project"].widget = forms.HiddenInput()
        return form

    def get_context_data(self, *args, **kwargs):
        pk = self.kwargs.get("pk")
        context = super().get_context_data(*args, **kwargs)
        context["project"] = get_object_or_404(Project, pk=pk)
        return context

    def get_success_url(self):
        return reverse("project-detail", kwargs={"pk": self.object.project_id})


class ProjectAttributeDeleteView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    model = ProjectAttribute
    form_class = ProjectAttributeDeleteForm
    template_name = "project/project_attribute_delete.html"

    def test_func(self):
        """UserPassesTestMixin Tests"""

        project_obj = get_object_or_404(Project, pk=self.kwargs.get("pk"))

        if self.request.user.is_superuser:
            return True

        if project_obj.pi == self.request.user:
            return True

        if project_obj.projectuser_set.filter(
            user=self.request.user, role__name="Manager", status__name="Active"
        ).exists():
            return True

        messages.error(self.request, "You do not have permission to add project attributes.")

    def get_avail_attrs(self, project_obj):
        if not self.request.user.is_superuser:
            avail_attrs = ProjectAttribute.objects.filter(project=project_obj, proj_attr_type__is_private=False)
        else:
            avail_attrs = ProjectAttribute.objects.filter(project=project_obj)
        avail_attrs_dicts = [
            {"pk": attr.pk, "selected": False, "name": str(attr.proj_attr_type), "value": attr.value}
            for attr in avail_attrs
        ]

        return avail_attrs_dicts

    def get(self, request, *args, **kwargs):
        pk = self.kwargs.get("pk")
        project_obj = get_object_or_404(Project, pk=pk)

        project_attributes_to_delete = self.get_avail_attrs(project_obj)
        context = {}

        if project_attributes_to_delete:
            formset = formset_factory(ProjectAttributeDeleteForm, max_num=len(project_attributes_to_delete))
            formset = formset(initial=project_attributes_to_delete, prefix="attributeform")
            context["formset"] = formset
        context["project"] = project_obj
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        pk = self.kwargs.get("pk")
        attr_to_delete = self.get_avail_attrs(pk)

        formset = formset_factory(ProjectAttributeDeleteForm, max_num=len(attr_to_delete))
        formset = formset(request.POST, initial=attr_to_delete, prefix="attributeform")

        attributes_deleted_count = 0

        if formset.is_valid():
            for form in formset:
                form_data = form.cleaned_data
                if form_data["selected"]:
                    attributes_deleted_count += 1

                    proj_attr = ProjectAttribute.objects.get(pk=form_data["pk"])

                    proj_attr.delete()

            messages.success(request, "Deleted {} attributes from project.".format(attributes_deleted_count))
        else:
            for error in formset.errors:
                messages.error(request, error)

        return HttpResponseRedirect(reverse("project-detail", kwargs={"pk": pk}))


class ProjectAttributeUpdateView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "project/project_attribute_update.html"

    def test_func(self):
        """UserPassesTestMixin Tests"""
        project_obj = get_object_or_404(Project, pk=self.kwargs.get("pk"))

        if self.request.user.is_superuser:
            return True

        if project_obj.pi == self.request.user:
            return True

        if project_obj.projectuser_set.filter(
            user=self.request.user, role__name="Manager", status__name="Active"
        ).exists():
            return True

    def get(self, request, *args, **kwargs):
        project_obj = get_object_or_404(Project, pk=self.kwargs.get("pk"))
        project_attribute_pk = self.kwargs.get("project_attribute_pk")

        if project_obj.projectattribute_set.filter(pk=project_attribute_pk).exists():
            project_attribute_obj = project_obj.projectattribute_set.get(pk=project_attribute_pk)

            project_attribute_update_form = ProjectAttributeUpdateForm(
                initial={
                    "pk": self.kwargs.get("project_attribute_pk"),
                    "name": project_attribute_obj,
                    "value": project_attribute_obj.value,
                    "type": project_attribute_obj.proj_attr_type,
                }
            )

            context = {}
            context["project_obj"] = project_obj
            context["project_attribute_update_form"] = project_attribute_update_form
            context["project_attribute_obj"] = project_attribute_obj

            return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        project_obj = get_object_or_404(Project, pk=self.kwargs.get("pk"))
        project_attribute_pk = self.kwargs.get("project_attribute_pk")

        if project_obj.projectattribute_set.filter(pk=project_attribute_pk).exists():
            project_attribute_obj = project_obj.projectattribute_set.get(pk=project_attribute_pk)

            if project_obj.status.name not in [
                "Active",
                "New",
            ]:
                messages.error(request, "You cannot update an attribute in an archived project.")
                return HttpResponseRedirect(
                    reverse(
                        "project-attribute-update",
                        kwargs={"pk": project_obj.pk, "project_attribute_pk": project_attribute_obj.pk},
                    )
                )

            project_attribute_update_form = ProjectAttributeUpdateForm(
                request.POST,
                initial={
                    "pk": self.kwargs.get("project_attribute_pk"),
                },
            )

            if project_attribute_update_form.is_valid():
                form_data = project_attribute_update_form.cleaned_data
                project_attribute_obj.value = form_data.get("new_value")
                project_attribute_obj.save()

                messages.success(request, "Attribute Updated.")
                return HttpResponseRedirect(reverse("project-detail", kwargs={"pk": project_obj.pk}))
            else:
                for error in project_attribute_update_form.errors.values():
                    messages.error(request, error)
                return HttpResponseRedirect(
                    reverse(
                        "project-attribute-update",
                        kwargs={"pk": project_obj.pk, "project_attribute_pk": project_attribute_obj.pk},
                    )
                )
