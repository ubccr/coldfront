# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0


from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404
from django.shortcuts import get_object_or_404, render
from django.utils.translation import gettext_lazy as _
from django.views.generic import View

from coldfront.ras import filtersets, forms, tables
from coldfront.ras.models import Project, ProjectInvite
from coldfront.registry import register_model_view
from coldfront.views import ViewTab, generic
from coldfront.views.object_actions import AddObject, BulkDelete, BulkExport, DeleteObject

#
# Project Invites
#


@register_model_view(ProjectInvite, "list", path="", detail=False)
class ProjectInviteListView(generic.ObjectListView):
    queryset = ProjectInvite.objects.all()
    filterset = filtersets.ProjectInviteFilterSet
    filterset_form = forms.ProjectInviteFilterSetForm
    table = tables.ProjectInviteTable
    actions = (
        AddObject,
        BulkDelete,
    )


@register_model_view(ProjectInvite)
class ProjectInviteView(generic.ObjectView):
    queryset = ProjectInvite.objects.all()
    actions = (
        AddObject,
        DeleteObject,
    )


@register_model_view(ProjectInvite, "add", detail=False)
class ProjectInviteEditView(generic.ObjectEditView):
    # Invites cannot be edited; this view is add-only.
    queryset = ProjectInvite.objects.all()
    form = forms.ProjectInviteForm

    def alter_object(self, obj, request, url_args, url_kwargs):
        if not obj.pk:
            obj.invited_by = request.user
        return super().alter_object(obj, request, url_args, url_kwargs)


@register_model_view(ProjectInvite, "delete")
class ProjectInviteDeleteView(generic.ObjectDeleteView):
    queryset = ProjectInvite.objects.all()


@register_model_view(ProjectInvite, "bulk_import", path="import", detail=False)
class ProjectInviteBulkImportView(generic.BulkImportView):
    # Bulk-import invites from CSV. Invite emails are sent by the post_save
    # signal on creation, so no additional hook is required here.
    queryset = ProjectInvite.objects.all()
    model_form = forms.ProjectInviteImportForm


@register_model_view(ProjectInvite, "bulk_delete", path="delete", detail=False)
class ProjectInviteBulkDeleteView(generic.BulkDeleteView):
    queryset = ProjectInvite.objects.all()
    filterset = filtersets.ProjectInviteFilterSet
    table = tables.ProjectInviteTable


#
# Project "Invites" tab
#


@register_model_view(Project, "invites")
class ProjectInviteTabView(generic.ObjectChildrenView):
    actions = (BulkExport, BulkDelete)
    queryset = Project.objects.all()
    child_model = ProjectInvite
    table = tables.ProjectInviteTable
    filterset = filtersets.ProjectInviteFilterSet
    filterset_form = forms.ProjectInviteFilterSetForm
    template_name = "ras/project/invites.html"
    tab = ViewTab(
        label=_("Invites"),
        visible=lambda obj: obj.invites.pending().exists(),
        badge=lambda obj: obj.invites.pending().count(),
        permission="ras.view_projectinvite",
        weight=150,
    )

    def get_children(self, request, parent):
        return parent.invites.pending().restrict(request.user, "view")


#
# Public invite acceptance
#


class AcceptInviteView(LoginRequiredMixin, View):
    """
    View for accepting a project invite.

    Login is required: the invite links a user to a project, so the invitee
    must be authenticated before the invite can be accepted. Anonymous
    visitors are redirected to login (with ``?next=`` preserved) by
    ``LoginRequiredMixin``.

    Acceptance is POST-only (a confirmation page is shown first) to prevent
    phishing attacks: opening the invite link never accepts the invite.

    Access is controlled by the secret invite code (never stored in plaintext).
    The code is the secret: no email-match check is performed against the
    authenticated user.

    Expired or already-accepted invites return HTTP 404 rather than a page.
    """

    def _get_pending_invite(self, code):
        invite = get_object_or_404(ProjectInvite, code_hash=ProjectInvite.hash_code(code))
        if invite.accepted_at is not None or invite.is_expired:
            raise Http404()
        return invite

    def get(self, request, code):
        invite = self._get_pending_invite(code)

        context = {"invite": invite, "accept_url": request.get_full_path()}
        return render(request, "ras/invite_accept.html", context)

    def post(self, request, code):
        invite = self._get_pending_invite(code)

        invite.accept(request.user)
        return render(request, "ras/invite_success.html", {"invite": invite})
