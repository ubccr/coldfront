# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from datetime import timedelta

from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.http import Http404
from django.shortcuts import render
from django.utils import timezone
from django.utils.module_loading import import_string
from django.views.generic import View


class HomeView(LoginRequiredMixin, View):
    template_name = "home.html"

    def get(self, request):
        from coldfront.core.models import ObjectType
        from coldfront.ras.choices import (
            AllocationChangeRequestStatusChoices,
            AllocationStatusChoices,
        )
        from coldfront.ras.models import Allocation, AllocationChangeRequest
        from coldfront.users.querysets import RestrictedQuerySet

        user = request.user
        now = timezone.now()

        # --- Role detection ---
        is_pi = user.owned_projects.exists()
        is_admin = user.is_staff or user.has_perm("ras.change_allocation")

        # --- Common data ---
        projects = []
        allocations = []
        resources = {}

        # --- PI / member projects and allocations ---
        if user.is_authenticated:
            for p in user.owned_projects.all():
                projects.append(p)
                for a in p.allocations.all():
                    allocations.append(a)
            for pu in user.projects.all():
                p = pu.project
                if p not in projects:
                    projects.append(p)
                for a in p.allocations.all():
                    if a not in allocations:
                        allocations.append(a)

        # --- Allocatable resources ---
        for ot in ObjectType.objects.with_feature("allocatable_resource").order_by("app_label", "model"):
            model_class = ot.model_class()
            if model_class is None:
                continue

            qs = model_class.objects.all()
            if issubclass(qs.__class__, RestrictedQuerySet):
                qs = qs.restrict(user, "view")

            if qs.exists():
                group = model_class._meta.verbose_name_plural.title()
                if group.startswith("Slurm"):
                    group = "Slurm"
                resources[group] = resources.get(group, [])

            for obj in qs:
                if obj.allocatable(user):
                    resources[group].append({"name": str(obj), "link": obj.get_absolute_url()})

        # --- Summary stats ---
        active_allocations = [a for a in allocations if a.status == AllocationStatusChoices.STATUS_ACTIVE]
        expiring_soon = [
            a
            for a in allocations
            if a.end_date
            and a.status == AllocationStatusChoices.STATUS_ACTIVE
            and a.end_date <= now + timedelta(days=30)
            and a.end_date > now
        ]

        # --- PI-specific data ---
        pending_change_requests = []
        if is_pi:
            owned_project_ids = user.owned_projects.values_list("pk", flat=True)
            pending_change_requests = list(
                AllocationChangeRequest.objects.filter(
                    allocation__project_id__in=owned_project_ids,
                    status__in=[
                        AllocationChangeRequestStatusChoices.STATUS_REQUESTED,
                        AllocationChangeRequestStatusChoices.STATUS_APPROVED,
                    ],
                )
                .select_related("allocation")
                .order_by("-created")[:10]
            )

        # --- Admin-specific data ---
        admin_pending_allocations = []
        admin_pending_change_requests = []
        admin_expired_allocations = []
        if is_admin:
            admin_pending_allocations = list(
                Allocation.objects.filter(
                    status__in=[
                        AllocationStatusChoices.STATUS_REQUESTED,
                        AllocationStatusChoices.STATUS_APPROVED,
                    ],
                )
                .select_related("project")
                .order_by("-created")[:10]
            )
            admin_pending_change_requests = list(
                AllocationChangeRequest.objects.filter(
                    status__in=[
                        AllocationChangeRequestStatusChoices.STATUS_REQUESTED,
                        AllocationChangeRequestStatusChoices.STATUS_APPROVED,
                    ],
                )
                .select_related("allocation")
                .order_by("-created")[:10]
            )
            admin_expired_allocations = list(
                Allocation.objects.filter(
                    status=AllocationStatusChoices.STATUS_EXPIRED,
                )
                .select_related("project")
                .order_by("-end_date")[:10]
            )

        return render(
            request,
            self.template_name,
            {
                "projects": projects,
                "resources": resources,
                "allocations": allocations,
                "active_allocations": active_allocations,
                "expiring_soon": expiring_soon,
                "is_pi": is_pi,
                "is_admin": is_admin,
                "pending_change_requests": pending_change_requests,
                "admin_pending_allocations": admin_pending_allocations,
                "admin_pending_change_requests": admin_pending_change_requests,
                "admin_expired_allocations": admin_expired_allocations,
            },
        )


class ObjectSelectorView(LoginRequiredMixin, View):
    template_name = "generic/object_selector.html"

    def get(self, request):
        model = self._get_model(request.GET.get("_model", ""))

        form_class = self._get_form_class(model)
        form = form_class(request.GET)

        if "_search" in request.GET:
            # Return only search results
            filterset = self._get_filterset_class(model)

            queryset = model.objects.restrict(request.user)
            if filterset:
                queryset = filterset(request.GET, queryset, request=request).qs

            return render(
                request,
                "generic/object_selector_results.html",
                {
                    "results": queryset[:100],
                },
            )

        return render(
            request,
            self.template_name,
            {
                "form": form,
                "model": model,
                "target_id": request.GET.get("target"),
            },
        )

    def _get_model(self, label):
        try:
            app_label, model_name = label.split(".")
            content_type = ContentType.objects.get_by_natural_key(app_label, model_name)
        except (ValueError, ObjectDoesNotExist):
            raise Http404
        return content_type.model_class()

    def _get_form_class(self, model):
        if hasattr(self, "form_class"):
            return self.form_class
        app_label = model._meta.app_label
        class_name = f"{model.__name__}FilterSetForm"
        return import_string(f"coldfront.{app_label}.forms.{class_name}")

    def _get_filterset_class(self, model):
        if hasattr(self, "filterset_class"):
            return self.filterset_class
        app_label = model._meta.app_label
        class_name = f"{model.__name__}FilterSet"
        return import_string(f"coldfront.{app_label}.filtersets.{class_name}")
