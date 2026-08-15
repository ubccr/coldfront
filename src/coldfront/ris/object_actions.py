# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django_cotton import render_component

from coldfront.views.object_actions import ObjectAction

__all__ = ("UnlinkFunding", "UnlinkPublications")


class UnlinkChildren(ObjectAction):
    """
    Bulk action for the project publications/funding tabs. Removes the selected
    child records' links to the *current* project only; the global Publication/
    Funding instances (and their links to other projects) are left untouched.

    Requires the custom ``ris.unlink_*`` permission on the child model. The
    button posts to a project-scoped unlink view (``url_name``) rather than the
    global ``bulk_delete`` view, so the parent project pk is resolved from the
    URL instead of a form/query parameter.
    """

    url_name = None
    label = _("Remove Selected")
    multi = True
    permissions_required = {"unlink"}
    template_name = "button.bulk_delete"

    @classmethod
    def render(cls, context, obj, **kwargs):
        request = context["request"]
        # obj is the child model class; the parent Project is in context.
        project = context["object"]
        ctx = {
            "perms": context["perms"],
            "request": request,
            "url": reverse(cls.url_name, kwargs={"pk": project.pk}),
            "url_params": cls.get_url_params(context),
            "label": cls.label,
            **cls.get_context(context, obj),
            **kwargs,
        }

        return render_component(request, cls.template_name, ctx)


class UnlinkPublications(UnlinkChildren):
    url_name = "ras:project_publication_bulk_unlink"


class UnlinkFunding(UnlinkChildren):
    url_name = "ras:project_funding_bulk_unlink"
