import csv
import json
import re
from typing import Union

from django import forms
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.forms import formset_factory
from django.http import HttpResponseRedirect, StreamingHttpResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views import View
from django.views.generic import FormView, ListView, TemplateView
from django.views.generic.edit import UpdateView
import requests

from django.contrib.auth.models import User
from coldfront.core.user.models import UserProfile
from coldfront.core.user.views import UserSelectResults
from coldfront.core.utils.common import Echo
from coldfront.core.grant.forms import GrantDeleteForm, GrantDownloadForm, GrantForm
from coldfront.core.grant.forms import (
    GrantDeleteForm,
    GrantForm,
    OrcidImportGrantQueryForm,
    OrcidImportGrantResultForm,
    )
from coldfront.core.grant.models import (Grant, GrantFundingAgency,
                                         GrantStatusChoice, GrantStaged)
from coldfront.core.project.models import Project, ProjectUser

from coldfront.plugins.orcid.orcid_vars import OrcidAPI
from coldfront.plugins.orcid.dict_methods import *
from coldfront.core.utils.common import import_from_settings

PLUGIN_ORCID = import_from_settings('PLUGIN_ORCID', False)
if PLUGIN_ORCID:
    ORCID_SANDBOX = import_from_settings('ORCID_SANDBOX', True)

class GrantCreateView(LoginRequiredMixin, UserPassesTestMixin, FormView):
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
        return reverse('project-detail', kwargs={'pk': self.kwargs.get('project_pk')})

class GrantCreateChoiceView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'grant/grant_create_choice.html'

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

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        project_obj = get_object_or_404(Project, pk=self.kwargs.get('project_pk'))

        user_query_set = project_obj.projectuser_set.select_related('user').filter(
            status__name__in=['Active', ]).order_by("user__username")

        if user_query_set:
            orcid_users = []
            for project_user in user_query_set:
                try:
                    user = project_user.user 
                    if ORCID_SANDBOX: 
                        orcid_is_linked = user.social_auth.get(provider='orcid-sandbox')
                    else:
                        orcid_is_linked = user.social_auth.get(provider='orcid')
                    orcid_users.append(user.username)
                except:
                    pass

        has_orcid_users = False 
        no_orcid_users = 'No project users have ORCID accounts linked'
        if orcid_users:
            has_orcid_users = True 
        context['project'] = Project.objects.get(pk=self.kwargs.get('project_pk'))
        context['orcid_vars'] = OrcidAPI.orcid_configured()
        context['has_orcid_users'] = has_orcid_users
        context['no_orcid_users'] = no_orcid_users
        context['orcid_config_msg'] = OrcidAPI.ORC_CONFIG_MSG
        return context


class GrantOrcidImportView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'grant/grant_orcid_import.html'
    
    def test_func(self):
        """ UserPassesTestMixin Tests"""
        if self.request.user.is_superuser:
            return True

        project_obj = get_object_or_404(Project, pk=self.kwargs.get('project_pk'))

        if project_obj.pi == self.request.user:
            return True

        if project_obj.projectuser_set.filter(user=self.request.user, role__name='Manager', status__name='Active').exists():
            return True

        messages.error(self.request, 'You do not have permission to import a new grant to this project.')
    
    def dispatch(self, request, *args, **kwargs):
        project_obj = get_object_or_404(Project, pk=self.kwargs.get('project_pk'))
        if project_obj.status.name not in ['Active', 'New', ]:
            messages.error(request, 'You cannot import grants to an archived project.')
            return HttpResponseRedirect(reverse('project-detail', kwargs={'pk': project_obj.pk}))
        else:
            return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)

        context['project'] = Project.objects.get(
            pk=self.kwargs.get('project_pk'))
            
        context['grant_orcid_query_form'] = OrcidImportGrantQueryForm(project_pk=self.kwargs.get('project_pk'))
        
        return context
    

    def post(self, request, *args, **kwargs):
        grants = eval(request.POST.get('grants'))
        project_pk = self.kwargs.get('project_pk')

        project_obj = get_object_or_404(Project, pk=project_pk)
        formset = formset_factory(OrcidImportGrantResultForm, max_num=len(grants))
        formset = formset(request.POST, initial=grants, prefix='grantform')

        grants_added = 0
        grants_updated = []
        grants_skipped = []

        if formset.is_valid():
            for form in formset:
                form_data = form.cleaned_data

                created = False
                updated = False

                if form_data['selected']:
                    statuses = list(GrantStatusChoice.objects.all())
                    stat_str = form_data.get('status')[0]
                    choosen_status = statuses[0]

                    for status in statuses:
                        if stat_str == status.name:
                            choosen_status = status
                    
                    choosen_grant_num = form_data.get('grant_number')

                    # Check if grant already exists
                    if choosen_grant_num:
                        try:
                            grant_obj = Grant.objects.filter(grant_number=choosen_grant_num)[0]

                            # Update grant
                            grant_obj.project=project_obj
                            grant_obj.title=form_data.get('title')
                            grant_obj.role=form_data.get('role')[0]
                            grant_obj.grant_pi_full_name=form_data.get('grant_pi_full_name')
                            grant_obj.grant_start=form_data.get('grant_start')
                            grant_obj.grant_end=form_data.get('grant_end')
                            grant_obj.total_amount_awarded=form_data.get('total_amount_awarded')
                            grant_obj.direct_funding=form_data.get('direct_funding')
                            grant_obj.percent_credit=form_data.get('percent_credit')

                            # Import may not have a funding adgency that is listed so default to other
                            grant_obj.funding_agency=list(GrantFundingAgency.objects.all())[-1]
                            grant_obj.other_funding_agency=form_data.get('funding_agency')
                            grant_obj.status=choosen_status

                            grant_obj.save()

                            updated = True
                        except IndexError:
                            updated = False # Grant does not exist

                    # Grant does not exists. Create it.
                    if not updated:
                        grant_obj, created = Grant.objects.get_or_create(
                            project=project_obj,
                            title=form_data.get('title'),
                            role=form_data.get('role')[0],
                            grant_pi_full_name=form_data.get('grant_pi_full_name'),
                            grant_number=form_data.get('grant_number'),
                            grant_start=form_data.get('grant_start'),
                            grant_end=form_data.get('grant_end'),
                            total_amount_awarded=form_data.get('total_amount_awarded'),
                            direct_funding=form_data.get('direct_funding'),
                            percent_credit=form_data.get('percent_credit'),
                            funding_agency=
                                list(GrantFundingAgency.objects.all())[-1],         # Import may not have a funding adgency that is listed
                            other_funding_agency=form_data.get('funding_agency'),   # so default to other
                            status=choosen_status,
                        )


                if created:
                    grants_added += 1
                elif updated:
                    grants_updated.append(form_data.get('title'))
                else:
                    grants_skipped.append(form_data.get('title'))

            if grants_added:
                messages.success(request, f'Added {grants_added} grant(s) to project.')

            if grants_updated:
               grants_updated = ', '.join(grants_updated) 
               messages.info(request, f'Updated: {grants_updated}')
                
            if grants_skipped:
                grants_skipped = ', '.join(grants_skipped)
                messages.warning(request, f'Grant(s) already exists on this project. Skipped adding: {grants_skipped}.')

        else:
            for error in formset.errors:
                messages.error(request, error)

        return HttpResponseRedirect(reverse('project-detail', kwargs={'pk': project_pk}))


class GrantOrcidImportResultView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'grant/grant_orcid_import_search_result.html'

    def test_func(self):
        """ UserPassesTestMixin Tests"""
        if self.request.user.is_superuser:
            return True

        project_obj = get_object_or_404(
            Project, pk=self.kwargs.get('project_pk'))

        if project_obj.pi == self.request.user:
            return True

        if project_obj.projectuser_set.filter(user=self.request.user, role__name='Manager', status__name='Active').exists():
            return True
    
    def dispatch(self, request, *args, **kwargs):
        project_obj = get_object_or_404(
            Project, pk=self.kwargs.get('project_pk'))
        if project_obj.status.name not in ['Active', 'New', ]:
            messages.error(
                request, 'You cannot import grants to an archived project.')
            return HttpResponseRedirect(reverse('project-detail', kwargs={'project_pk': project_obj.pk}))
        else:
            return super().dispatch(request, *args, **kwargs)

    def _search_id(self, unique_id) -> Union[dict, bool]:
        def get_grant_date(date: dict) -> str:
            '''
            Returns the date in string form
            '''
            default_date = "9999-12-31"
            date_str : str = ""
            yr = get_value_or_default(date, "year", "value",
                    default_value=None)
            
            if not yr:
                return default_date
            
            month = get_value_or_default(date, "month", "value",
                    default_value=None)
            
            if not month:
                return default_date
            
            day = get_value_or_default(date, "month", "value",
                    default_value=None)
            
            if day:
                date_str = f"{yr}-{month}-{day}"
            else:
                return default_date
            
            return date_str
        

        # Regex the ORCID id from input
        orc_id_match = re.search(OrcidAPI.ORC_RE_KEY, unique_id)
        
        orc_grant_list = []

        if (orc_id_match):
            orc_id : str = orc_id_match.group()

            orc_token = OrcidAPI.orc_api.get_search_token_from_orcid()

            # Can only find researchers in sandbox env if app is in sandbox
            orc_record : dict = OrcidAPI.orc_api.read_record_public(orc_id, 'fundings', orc_token)

            orc_grants = orc_record['group']
            orc_grantsummary = [grants['funding-summary'][0] for grants in orc_grants]

            for grant in orc_grantsummary:
                orc_grant_info = {}

                putcode = grant['put-code']
                orc_grant_full = OrcidAPI.orc_api.read_record_public(orc_id, f'funding/{putcode}', orc_token)

                orc_grant_info['title'] = get_value_or_default(
                    orc_grant_full, "title", "title", "value",
                    default_value="[No Title]") 
                
                # Get external-ids for grant number
                external_ids : list = get_value_or_default(
                    orc_grant_full, "external-ids",
                    default_value=[]
                )

                external_id_set = False

                if external_ids:
                    for id in external_ids['external-id']:
                        if id['external-id-type'] == "grant_number":
                            orc_grant_info['grant_number'] = get_value_or_default(
                                id, "external-id-value", default_value="[None]"
                            )
                            external_id_set = True
                            break
                
                if not external_id_set:
                    orc_grant_info['grant_number'] = "[None]"

                orc_grant_info['funding_agency'] = get_value_or_default(
                    orc_grant_full, "organization", "name",
                    default_value="[No Funding Agency]")
                
                # Get grant start and end dates
                grant_start_date = get_value_or_default(orc_grant_full, "start-date",
                    default_value={})
                grant_end_date = get_value_or_default(orc_grant_full, "end-date",
                    default_value={})
                
                orc_grant_info['grant_start'] = get_grant_date(grant_start_date)
                orc_grant_info['grant_end'] = get_grant_date(grant_end_date)
                
                orc_grant_info['total_amount_awarded'] = get_value_or_default(
                    orc_grant_full, "amount", "value",
                    default_value=0)
                orc_grant_info['amount_awarded_currency'] = get_value_or_default(
                    orc_grant_full, "amount", "currency-code",
                    default_value="XXX"
                )
                orc_grant_info['unique_id'] = get_value_or_default(orc_grant_full, "path",
                    default_value="[No ID]").strip("/")


                try:
                    stored_grant = Grant.objects.filter(grant_number=orc_grant_info['grant_number'])[0]
                except KeyError:
                    stored_grant = None
                except IndexError:
                    stored_grant = None

                if stored_grant:
                    orc_grant_info['percent_credit'] = stored_grant.percent_credit
                    orc_grant_info['direct_funding'] = stored_grant.direct_funding
                    orc_grant_info['grant_pi_full_name'] = stored_grant.grant_pi_full_name
                    orc_grant_info['role'] = stored_grant.role
                    orc_grant_info['status'] = stored_grant.status.name

                orc_grant_list.append(orc_grant_info)

        return orc_grant_list

    def post(self, request, *args, **kwargs):
        project_pk = self.kwargs.get('project_pk')
        data = (request.POST)
        form_data = json.loads(data.get('form_info'))

        project_obj = get_object_or_404(Project, pk=project_pk)
        grants = []

        #Grab ORCID search ID's from users that have one
        search_ids = []
        for user in form_data:
            try:
                user_obj = User.objects.get(username__exact=user)
                orcid_user = user_obj.social_auth.get(provider='orcid-sandbox')
                search_ids.append(orcid_user.uid)
            except:
                pass 

        try:
            for ele in search_ids:
                grant_dict = self._search_id(ele)
                if grant_dict:
                    for grant_dict_entree in grant_dict:
                        if grant_dict_entree:
                            grants.append(grant_dict_entree)
        except requests.exceptions.HTTPError:
            context = {
                'orcid_not_found': True,
                'project_pk': project_pk
                }
            return render(request, self.template_name, context)

        formset = formset_factory(OrcidImportGrantResultForm, max_num=len(grants))
        formset = formset(initial=grants, prefix='grantform')



        context = {}
        context['orcid_not_found'] = False
        context['project_pk'] = project_obj.pk
        context['formset'] = formset
        context['search_ids'] = search_ids
        context['grants'] = grants

        return render(request, self.template_name, context)

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
              'other_award_number', 'grant_start', 'grant_end', 'percent_credit', 'direct_funding', 'total_amount_awarded', 'status', ]

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
        else:
            for error in formset.errors:
                messages.error(request, error)

        return HttpResponseRedirect(reverse('project-detail', kwargs={'pk': project_obj.pk}))

    def get_success_url(self):
        return reverse('project-detail', kwargs={'pk': self.object.project.id})


class GrantReportView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    template_name = 'grant/grant_report_list.html'

    def test_func(self):
        """ UserPassesTestMixin Tests"""
        if self.request.user.is_superuser:
            return True

        if self.request.user.has_perm('grant.can_view_all_grants'):
            return True

        messages.error(self.request, 'You do not have permission to view all grants.')


    def get_grants(self):
        grants = Grant.objects.prefetch_related(
            'project', 'project__pi').all().order_by('-total_amount_awarded')
        grants= [

            {'pk': grant.pk,
            'title': grant.title,
            'project_pk': grant.project.pk,
            'pi_first_name': grant.project.pi.first_name,
            'pi_last_name':grant.project.pi.last_name,
            'role': grant.role,
            'grant_pi': grant.grant_pi,
            'total_amount_awarded': grant.total_amount_awarded,
            'funding_agency': grant.funding_agency,
            'grant_number': grant.grant_number,
            'grant_start': grant.grant_start,
            'grant_end': grant.grant_end,
            'percent_credit': grant.percent_credit,
            'direct_funding': grant.direct_funding,
            }
            for grant in grants
        ]

        return grants


    def get(self, request, *args, **kwargs):
        context = {}
        grants = self.get_grants()

        if grants:
            formset = formset_factory(GrantDownloadForm, max_num=len(grants))
            formset = formset(initial=grants, prefix='grantdownloadform')
            context['formset'] = formset
        return render(request, self.template_name, context)


    def post(self, request, *args, **kwargs):
        grants = self.get_grants()

        formset = formset_factory(GrantDownloadForm, max_num=len(grants))
        formset = formset(request.POST, initial=grants, prefix='grantdownloadform')

        header = [
            'Grant Title',
            'Project PI',
            'Faculty Role',
            'Grant PI',
            'Total Amount Awarded',
            'Funding Agency',
            'Grant Number',
            'Start Date',
            'End Date',
            'Percent Credit',
            'Direct Funding',
        ]
        rows = []
        grants_selected_count = 0

        if formset.is_valid():
            for form in formset:
                form_data = form.cleaned_data
                if form_data['selected']:
                    grant = get_object_or_404(Grant, pk=form_data['pk'])

                    row = [
                        grant.title,
                        ' '.join((grant.project.pi.first_name, grant.project.pi.last_name)),
                        grant.role,
                        grant.grant_pi_full_name,
                        grant.total_amount_awarded,
                        grant.funding_agency,
                        grant.grant_number,
                        grant.grant_start,
                        grant.grant_end,
                        grant.percent_credit,
                        grant.direct_funding,
                    ]

                    rows.append(row)
                    grants_selected_count += 1

            if grants_selected_count == 0:
                grants = Grant.objects.prefetch_related('project', 'project__pi').all().order_by('-total_amount_awarded')
                for grant in grants:
                    row = [
                        grant.title,
                        ' '.join((grant.project.pi.first_name, grant.project.pi.last_name)),
                        grant.role,
                        grant.grant_pi_full_name,
                        grant.total_amount_awarded,
                        grant.funding_agency,
                        grant.grant_number,
                        grant.grant_start,
                        grant.grant_end,
                        grant.percent_credit,
                        grant.direct_funding,
                    ]
                    rows.append(row)

            rows.insert(0, header)
            pseudo_buffer = Echo()
            writer = csv.writer(pseudo_buffer)
            response = StreamingHttpResponse((writer.writerow(row) for row in rows),
                                            content_type="text/csv")
            response['Content-Disposition'] = 'attachment; filename="grants.csv"'
            return response
        else:
            for error in formset.errors:
                messages.error(request, error)
            return HttpResponseRedirect(reverse('grant-report'))


class GrantDownloadView(LoginRequiredMixin, UserPassesTestMixin, View):
    login_url = "/"

    def test_func(self):
        """ UserPassesTestMixin Tests"""
        if self.request.user.is_superuser:
            return True

        if self.request.user.has_perm('grant.can_view_all_grants'):
            return True

        messages.error(self.request, 'You do not have permission to download all grants.')

    def get(self, request):

        header = [
            'Grant Title',
            'Project PI',
            'Faculty Role',
            'Grant PI',
            'Total Amount Awarded',
            'Funding Agency',
            'Grant Number',
            'Start Date',
            'End Date',
            'Percent Credit',
            'Direct Funding',
        ]

        rows = []
        grants = Grant.objects.prefetch_related('project', 'project__pi').all().order_by('-total_amount_awarded')
        for grant in grants:
            row = [
                grant.title,
                ' '.join((grant.project.pi.first_name, grant.project.pi.last_name)),
                grant.role,
                grant.grant_pi_full_name,
                grant.total_amount_awarded,
                grant.funding_agency,
                grant.grant_number,
                grant.grant_start,
                grant.grant_end,
                grant.percent_credit,
                grant.direct_funding,
            ]

            rows.append(row)
        rows.insert(0, header)
        pseudo_buffer = Echo()
        writer = csv.writer(pseudo_buffer)
        response = StreamingHttpResponse((writer.writerow(row) for row in rows),
                                         content_type="text/csv")
        response['Content-Disposition'] = 'attachment; filename="grants.csv"'
        return response
