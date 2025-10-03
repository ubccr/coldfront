# SPDX-FileCopyrightText: (C) ColdFront Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging

from django.apps import apps
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import FieldDoesNotExist
from django.forms import formset_factory
from django.http import HttpResponseBadRequest, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.views.generic.base import TemplateView

from coldfront.core.tag.forms import TagEditForm
from coldfront.core.tag.models import Tag

logger = logging.getLogger(__name__)


def get_tag_field_name(other_obj):
    try:
        return Tag.get_tag_field_name(other_obj)
    except FieldDoesNotExist as e:
        raise HttpResponseBadRequest(e)


def get_tags_to_edit(obj, user):
    tag_field_name = get_tag_field_name(obj)
    existing_qs = Tag.get_tags_visible_to_user(getattr(obj, tag_field_name).all(), user)
    allowed_qs = Tag.get_tags_visible_to_user(Tag.get_allowed_tags_for(obj.__class__), user).difference(existing_qs)
    tag_data = {
        "add": [
            {
                "pk": tag.pk,
                "name": str(tag),
                "html_classes": tag.get_html_classes,
            }
            for tag in allowed_qs
        ],
        "remove": [
            {
                "pk": tag.pk,
                "name": str(tag),
                "html_classes": tag.get_html_classes,
            }
            for tag in existing_qs
        ],
    }
    return tag_data


class TagsEditView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "tag/tags_edit.html"

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        if not self.model:
            app_label = self.kwargs.get("app_label")
            model_name = self.kwargs.get("model_name")
            self.model = apps.get_model(app_label=app_label, model_name=model_name)

    def test_func(self):
        """UserPassesTestMixin Tests"""
        if self.request.user.is_superuser:
            return True
        messages.error(self.request, "You do not have permission to edit tags.")
        return False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        pk = self.kwargs.get("pk")

        other_obj = get_object_or_404(self.model, pk=pk)

        tag_data = get_tags_to_edit(other_obj, self.request.user)
        add_list = tag_data["add"]
        remove_list = tag_data["remove"]
        # Add formset
        if add_list:
            AddTagFormset = formset_factory(TagEditForm, max_num=len(add_list))
            add_formset = AddTagFormset(initial=add_list, prefix="tag_add_form")
            context["add_formset"] = add_formset
        # Remove formset
        if remove_list:
            RemoveTagFormset = formset_factory(TagEditForm, max_num=len(remove_list))
            remove_formset = RemoveTagFormset(initial=remove_list, prefix="tag_remove_form")
            context["remove_formset"] = remove_formset

        context["other_obj"] = other_obj
        context["other_obj_name"] = other_obj.__class__.__name__
        context["back_redirect"] = self.request.GET.get("redirect_path")

        return context

    def post(self, request, *args, **kwargs):
        app_label = self.kwargs.get("app_label")
        model_name = self.kwargs.get("model_name")
        pk = self.kwargs.get("pk")
        Model = apps.get_model(app_label=app_label, model_name=model_name)
        other_obj = get_object_or_404(Model, pk=pk)
        tag_field_name = get_tag_field_name(other_obj)
        obj_tags = getattr(other_obj, tag_field_name)

        tag_data = get_tags_to_edit(other_obj, self.request.user)
        add_list = tag_data["add"]
        remove_list = tag_data["remove"]

        # Add formset
        if add_list:
            AddTagFormset = formset_factory(TagEditForm, max_num=len(add_list))
            add_formset = AddTagFormset(request.POST, initial=add_list, prefix="tag_add_form")
            if add_formset.is_valid():
                tag_pks_to_add = [form["pk"] for form in add_formset.cleaned_data if form["selected"]]
                tags_to_add = Tag.objects.filter(pk__in=tag_pks_to_add)
                if tags_to_add:
                    obj_tags.add(*tags_to_add)
                    messages.success(request, f"Added {len(tags_to_add)} tag(s) to {other_obj.__class__.__name__}.")
            else:
                for error in add_formset.errors:
                    messages.error(request, error)

        # Remove formset
        if remove_list:
            RemoveTagFormset = formset_factory(TagEditForm, max_num=len(remove_list))
            remove_formset = RemoveTagFormset(request.POST, initial=remove_list, prefix="tag_remove_form")
            if remove_formset.is_valid():
                tag_pks_to_remove = [form["pk"] for form in remove_formset.cleaned_data if form["selected"]]
                tags_to_remove = Tag.objects.filter(pk__in=tag_pks_to_remove)
                if tags_to_remove:
                    obj_tags.remove(*tags_to_remove)
                    messages.success(
                        request, f"Removed {len(tags_to_remove)} tag(s) from {other_obj.__class__.__name__}."
                    )
            else:
                for error in remove_formset.errors:
                    messages.error(request, error)

        return HttpResponseRedirect(self.request.GET.get("redirect_path"))
