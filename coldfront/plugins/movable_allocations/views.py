import logging

from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import HttpResponseNotFound, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views.generic import TemplateView

from coldfront.core.allocation.utils import create_admin_action
from coldfront.core.project.utils import generate_slurm_account_name
from coldfront.core.utils.common import get_domain_url
from coldfront.core.utils.mail import send_allocation_customer_email, send_allocation_admin_email
from coldfront.core.utils.groups import check_if_groups_in_review_groups
from coldfront.core.allocation.models import Allocation, AllocationAttribute, AllocationUserNote
from coldfront.core.project.models import (
    Project,
    ProjectUser,
    ProjectUserRoleChoice,
    ProjectUserStatusChoice,
    ProjectUserMessage,
)
from coldfront.plugins.movable_allocations.forms import AllocationMoveForm
from coldfront.plugins.movable_allocations.utils import (
    check_over_allocation_limit,
    check_resource_is_allowed,
)
from coldfront.plugins.movable_allocations.signals import allocation_moved

logger = logging.getLogger(__name__)


class AllocationMoveView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "movable_allocations/allocation_move.html"

    def test_func(self):
        allocation_obj = get_object_or_404(Allocation, pk=self.kwargs.get("pk"))
        if self.request.user.is_superuser:
            return True

        group_exists = check_if_groups_in_review_groups(
            allocation_obj.get_parent_resource.review_groups.all(),
            self.request.user.groups.all(),
            "can_move_allocations",
        )
        if group_exists:
            return True

        messages.error(self.request, "You do not have permission to move this allocation.")
        return False

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_superuser:
            return super().dispatch(request, *args, **kwargs)

        allocation_obj = get_object_or_404(Allocation, pk=kwargs.get("pk"))
        if not allocation_obj.status.name == "Active":
            messages.error(request, "You cannot move an inactive allocation.")
            return HttpResponseRedirect(
                reverse("allocation-detail", kwargs={"pk": kwargs.get("pk")})
            )

        if not allocation_obj.project.status.name == "Active":
            messages.error(request, "You cannot move an allocation in an inactive project.")
            return HttpResponseRedirect(
                reverse("allocation-detail", kwargs={"pk": kwargs.get("pk")})
            )

        if allocation_obj.is_locked:
            messages.error(request, "You cannot move a locked allocation")
            return HttpResponseRedirect(
                reverse("allocation-detail", kwargs={"pk": kwargs.get("pk")})
            )

        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        pk = self.kwargs.get("pk")
        allocation_obj = get_object_or_404(Allocation, pk=pk)
        form = AllocationMoveForm()
        context = self.get_context_data()
        context["form"] = form
        context["allocation"] = allocation_obj
        context["allocation_users"] = allocation_obj.allocationuser_set.filter(
            status__name="Active"
        )
        context["allocation_attributes"] = allocation_obj.allocationattribute_set.filter(
            allocation_attribute_type__is_private=False
        )
        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        pk = self.kwargs.get("pk")
        allocation_obj = get_object_or_404(Allocation, pk=pk)
        origin_project_obj = allocation_obj.project

        form = AllocationMoveForm(request.POST)
        if not form.is_valid():
            for error in form.errors:
                messages.error(request, error)
            return HttpResponseRedirect(reverse("move-allocation", kwargs={"pk": pk}))

        destination_project_obj = Project.objects.filter(
            id=form.cleaned_data.get("destination_project")
        ).first()
        if not destination_project_obj:
            messages.error(
                request,
                "This project does not exist.",
            )
            return HttpResponseRedirect(reverse("move-allocation", kwargs={"pk": pk}))

        allocation_objs = destination_project_obj.allocation_set.filter(
            status__name__in=["Active", "New", "Renewal Requested"],
            resources=allocation_obj.get_parent_resource,
        )
        if allocation_obj in allocation_objs:
            messages.error(
                request,
                "This allocation is already in this project.",
            )
            return HttpResponseRedirect(reverse("move-allocation", kwargs={"pk": pk}))

        if check_over_allocation_limit(allocation_obj, allocation_objs):
            messages.error(
                request,
                "Moving this allocation to this project will put it over its resource limit.",
            )
            return HttpResponseRedirect(reverse("move-allocation", kwargs={"pk": pk}))

        if not check_resource_is_allowed(allocation_obj, destination_project_obj):
            messages.error(
                request, "The resource in this allocation is not allowed in this type of project."
            )
            return HttpResponseRedirect(reverse("move-allocation", kwargs={"pk": pk}))

        create_admin_action(
            user=request.user,
            fields_to_check={"project": destination_project_obj},
            allocation=allocation_obj,
        )

        allocation_obj.project = destination_project_obj
        allocation_obj.save()

        slurm_account_obj = AllocationAttribute.objects.filter(
            allocation=allocation_obj,
            allocation_attribute_type__name="slurm_account_name"
        ).first()
        if slurm_account_obj:
            slurm_account_obj.value = generate_slurm_account_name(allocation_obj.project)
            slurm_account_obj.save()

        project_user_active_status = ProjectUserStatusChoice.objects.get(name="Active")
        project_users_removed_status = ProjectUserStatusChoice.objects.get(name="Removed")
        auto_disable = allocation_obj.project.projectattribute_set.filter(
            proj_attr_type__name="Auto Disable User Notifications"
        ).first()
        enable_notifications = not (auto_disable and auto_disable.value == "Yes")
        for allocation_user in allocation_obj.allocationuser_set.all():
            project_user_obj = destination_project_obj.projectuser_set.filter(
                user=allocation_user.user
            ).first()
            if project_user_obj:
                if not project_user_obj.status.name == "Active":
                    if allocation_user.status.name in ["Active", "Invited", "Disabled", "Retired"]:
                        project_user_obj.status = project_user_active_status
                        project_user_obj.save()
            else:
                project_user = origin_project_obj.projectuser_set.get(user=allocation_user.user)
                role = "Group" if project_user.role.name == "Group" else "User"
                status = project_user_active_status
                if allocation_user.status.name not in ["Active", "Invited", "Disabled", "Retired"]:
                    status = project_users_removed_status
                project_user_obj = ProjectUser.objects.create(
                    user=allocation_user.user,
                    project=destination_project_obj,
                    role=ProjectUserRoleChoice.objects.get(name=role),
                    status=status,
                    enable_notifications=enable_notifications,
                )

        domain_url = get_domain_url(request)
        destination_project_url = (
            f"{domain_url}{reverse('project-detail', kwargs={'pk': destination_project_obj.pk})}"
        )
        origin_project_url = (
            f"{domain_url}{reverse('project-detail', kwargs={'pk': origin_project_obj.pk})}"
        )
        allocation_url = (
            f"{domain_url}{reverse('allocation-detail', kwargs={'pk': allocation_obj.pk})}"
        )
        AllocationUserNote.objects.create(
            allocation=allocation_obj,
            author=User.objects.get(username="coldft"),
            is_private=False,
            note=f"{request.user.first_name} {request.user.last_name} ({request.user.username}) "
            f'moved this allocation from project "{origin_project_obj.title}", {origin_project_url}'
            f', to project "{destination_project_obj.title}", {destination_project_url}.',
        )

        ProjectUserMessage.objects.create(
            project=origin_project_obj,
            author=User.objects.get(username="coldft"),
            is_private=False,
            message=f"{request.user.first_name} {request.user.last_name} ({request.user.username}) "
            f"moved a {allocation_obj.get_parent_resource} allocation, {allocation_url}, from this "
            f'project to project "{destination_project_obj.title}", {destination_project_url}.',
        )

        ProjectUserMessage.objects.create(
            project=destination_project_obj,
            author=User.objects.get(username="coldft"),
            is_private=False,
            message=f"{request.user.first_name} {request.user.last_name} ({request.user.username}) "
            f"moved a {allocation_obj.get_parent_resource} allocation, {allocation_url}, from project "
            f'"{origin_project_obj.title}", {origin_project_url}, to this project.',
        )

        addtl_context = {
            "user": self.request.user,
            "resource": allocation_obj.get_parent_resource,
            "destination_project_url": destination_project_url,
            "origin_project_url": origin_project_url,
            "allocation_url": allocation_url,
        }
        send_allocation_customer_email(
            allocation_obj,
            "Allocation Moved",
            "movable_allocations/email/moved_allocation.txt",
            addtl_context=addtl_context,
        )
        send_allocation_admin_email(
            allocation_obj,
            "Allocation Moved",
            "movable_allocations/email/moved_allocation_admin.txt",
            addtl_context=addtl_context,
        )

        allocation_moved.send(
            sender=self.__class__,
            allocation_pk=allocation_obj.pk,
            origin_project_pk=origin_project_obj.pk,
            destination_project_pk=destination_project_obj.pk,
        )

        logger.info(
            f"Admin {request.user.username} moved allocation {allocation_obj.pk} from project "
            f"{origin_project_obj.pk} to project {destination_project_obj.pk}"
        )

        messages.success(request, "Your allocation was successfully moved.")

        return HttpResponseRedirect(reverse("allocation-detail", kwargs={"pk": pk}))


class ProjectDetailView(LoginRequiredMixin, TemplateView):
    template_name = "movable_allocations/project_detail.html"

    def dispatch(self, request, *args, **kwargs):
        if request.META.get("HTTP_REFERER") is None:
            return HttpResponseNotFound(render(request, "404.html", {}))
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        project_pk = self.kwargs.get("project_pk")
        allocation_pk = self.kwargs.get("pk")
        context = self.get_context_data()
        context["does_not_exist"] = False
        project_obj = Project.objects.filter(id=project_pk).first()
        if not project_obj:
            context["does_not_exist"] = True
            return self.render_to_response(context)

        allocation_obj = get_object_or_404(Allocation, pk=allocation_pk)
        context["project"] = project_obj
        allocation_objs = project_obj.allocation_set.filter(
            status__name__in=["Active", "New", "Renewal Requested"]
        )
        context["already_in_project"] = allocation_obj in allocation_objs
        context["allocations"] = allocation_objs
        context["over_allocation_limit"] = check_over_allocation_limit(
            allocation_obj, allocation_objs
        )
        context["resource_allowed"] = check_resource_is_allowed(allocation_obj, project_obj)

        return self.render_to_response(context)
