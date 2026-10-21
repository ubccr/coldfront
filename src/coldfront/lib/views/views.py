# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from datetime import timedelta

from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from django.http import Http404
from django.shortcuts import render
from django.utils import timezone
from django.utils.module_loading import import_string
from django.views.generic import View
from generic_notifications.utils import get_notifications


class HomeView(LoginRequiredMixin, View):
    template_name = "home/index.html"

    def get(self, request):
        from coldfront.core.models import CommentEntry
        from coldfront.ras.choices import (
            AllocationChangeRequestStatusChoices,
            AllocationStatusChoices,
        )
        from coldfront.ras.models import Allocation, AllocationChangeRequest, Project, ProjectUser

        user = request.user
        now = timezone.now()
        expiring_soon_date = now + timedelta(days=30)

        stats = {
            "active_allocations": Allocation.objects.restrict(user, "view")
            .filter(status=AllocationStatusChoices.STATUS_ACTIVE)
            .count(),
            "expiring_soon": Allocation.objects.restrict(user, "view")
            .filter(status=AllocationStatusChoices.STATUS_ACTIVE, end_date__gt=now, end_date__lt=expiring_soon_date)
            .count(),
            "pending_change_requests": AllocationChangeRequest.objects.restrict(user, "view")
            .filter(
                Q(status=AllocationChangeRequestStatusChoices.STATUS_REQUESTED)
                | Q(status=AllocationChangeRequestStatusChoices.STATUS_APPROVED)
            )
            .count(),
            "projects": Project.objects.restrict(user, "view").count(),
            "allocations": Allocation.objects.restrict(user, "view").count(),
            "resources": len(user.requestable_resources),
            "project_users": ProjectUser.objects.restrict(user, "view").count(),
            "project_last_updated": None,
            "comments": CommentEntry.objects.restrict(user, "view").count(),
        }

        allocations = list(Allocation.objects.restrict(user, "view").order_by("-last_updated"))[:10]
        projects = list(Project.objects.restrict(user, "view").order_by("-last_updated"))[:5]
        comments = CommentEntry.objects.restrict(user, "view").order_by("-created")[:15]

        if len(projects) > 1:
            stats["project_last_updated"] = projects[0].last_updated

        stats["read_notifications_count"] = get_notifications(user=user).filter(read__isnull=False).count()

        return render(
            request,
            self.template_name,
            {
                "projects": projects,
                "allocations": allocations,
                "notifications": get_notifications(user=user),
                "comments": comments,
                "stats": stats,
                "expiring_soon_date": expiring_soon_date,
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
