from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.forms import formset_factory
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views.generic import DetailView, FormView, ListView, TemplateView
from django.views.generic.edit import CreateView, UpdateView

from core.djangoapps.grant.forms import GrantDeleteForm, GrantForm
from core.djangoapps.grant.models import (Grant, GrantFundingAgency,
                                          GrantStatusChoice)
from core.djangoapps.project.models import Project


class GrantCreateView(FormView):
    form_class = GrantForm
    template_name = 'grant/grant_create.html'

    def test_func(self):
        """ UserPassesTestMixin Tests"""
        if self.request.user.is_superuser:
            return True

        project_obj = get_object_or_404(Project, pk=self.kwargs.get('project_pk'))

        if project_obj.pi == self.request.user:
            return True

        if project_obj.projectuser_set.filter(user=self.request.user, role__name='Manager', status__name='Active').exists():
            return True

        messages.error(self.request, 'You do not have permission to add a new grant to this project.')

    def dispatch(self, request, *args, **kwargs):
        project_obj = get_object_or_404(Project, pk=self.kwargs.get('project_pk'))
        if project_obj.status.name not in ['Active', 'New', ]:
            messages.error(request, 'You cannot add grants to an archived project.')
            return HttpResponseRedirect(reverse('project-detail', kwargs={'pk': project_obj.pk}))
        else:
            return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form_data = form.cleaned_data
        project_obj = get_object_or_404(Project, pk=self.kwargs.get('project_pk'))
        grant_obj = Grant.objects.create(
            project=project_obj,
            title=form_data.get('title'),
            grant_number=form_data.get('grant_number'),
            role=form_data.get('role'),
            grant_pi_full_name=form_data.get('grant_pi_full_name'),
            funding_agency=form_data.get('funding_agency'),
            other_funding_agency=form_data.get('other_funding_agency'),
            other_award_number=form_data.get('other_award_number'),
            grant_start=form_data.get('grant_start'),
            grant_end=form_data.get('grant_end'),
            percent_credit=form_data.get('percent_credit'),
            direct_funding=form_data.get('direct_funding'),
            total_amount_awarded=form_data.get('total_amount_awarded'),
            status=form_data.get('status'),
        )

        return super().form_valid(form)

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context['project'] = Project.objects.get(pk=self.kwargs.get('project_pk'))
        return context


    def get_success_url(self):
        messages.success(self.request, 'Added a grant.')
        return reverse('project-detail', kwargs={'pk':self.kwargs.get('project_pk')})


class GrantUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    def test_func(self):
        """ UserPassesTestMixin Tests"""
        if self.request.user.is_superuser:
            return True

        grant_obj = get_object_or_404(Grant, pk=self.kwargs.get('pk'))

        if grant_obj.project.pi == self.request.user:
            return True

        if grant_obj.project.projectuser_set.filter(user=self.request.user, role__name='Manager', status__name='Active').exists():
            return True

        messages.error(self.request, 'You do not have permission to update grant from this project.')

    model = Grant
    template_name_suffix = '_update_form'
    fields = ['title', 'grant_number', 'role', 'grant_pi_full_name', 'funding_agency', 'other_funding_agency',
              'other_award_number', 'grant_start', 'grant_end', 'percent_credit', 'direct_funding', 'total_amount_awarded', 'status',]

    def get_success_url(self):
        return reverse('project-detail', kwargs={'pk': self.object.project.id})


class GrantDeleteGrantsView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'grant/grant_delete_grants.html'

    def test_func(self):
        """ UserPassesTestMixin Tests"""
        if self.request.user.is_superuser:
            return True

        project_obj = get_object_or_404(Project, pk=self.kwargs.get('project_pk'))

        if project_obj.pi == self.request.user:
            return True

        if project_obj.projectuser_set.filter(user=self.request.user, role__name='Manager', status__name='Active').exists():
            return True

        messages.error(self.request, 'You do not have permission to delete grants from this project.')

    def get_grants_to_delete(self, project_obj):

        grants_to_delete = [

            {'title': grant.title,
             'grant_number': grant.grant_number,
             'grant_end': grant.grant_end}

            for grant in project_obj.grant_set.all()
        ]

        return grants_to_delete

    def get(self, request, *args, **kwargs):
        project_obj = get_object_or_404(Project, pk=self.kwargs.get('project_pk'))

        grants_to_delete = self.get_grants_to_delete(project_obj)
        context = {}

        if grants_to_delete:
            formset = formset_factory(GrantDeleteForm, max_num=len(grants_to_delete))
            formset = formset(initial=grants_to_delete, prefix='grantform')
            context['formset'] = formset

        context['project'] = project_obj
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        project_obj = get_object_or_404(Project, pk=self.kwargs.get('project_pk'))

        grants_to_delete = self.get_grants_to_delete(project_obj)
        context = {}

        formset = formset_factory(GrantDeleteForm, max_num=len(grants_to_delete))
        formset = formset(request.POST, initial=grants_to_delete, prefix='grantform')

        grants_deleted_count = 0

        if formset.is_valid():
            for form in formset:
                grant_form_data = form.cleaned_data
                if grant_form_data['selected']:

                    grant_obj = Grant.objects.get(
                        project=project_obj,
                        title=grant_form_data.get('title'),
                        grant_number=grant_form_data.get('grant_number')
                    )
                    grant_obj.delete()
                    grants_deleted_count += 1

            messages.success(request, 'Deleted {} grants from project.'.format(grants_deleted_count))
            return HttpResponseRedirect(reverse('project-detail', kwargs={'pk': project_obj.pk}))

    def get_success_url(self):
        return reverse('project-detail', kwargs={'pk': self.object.project.id})
