from django.shortcuts import render
import csv
import datetime
import logging
from datetime import date
import json

from dateutil.relativedelta import relativedelta
from django import forms
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.models import User
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import Q
from django.db.models.query import QuerySet
from django.forms import formset_factory
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse, HttpResponseBadRequest, StreamingHttpResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse, reverse_lazy
from django.utils.html import format_html, mark_safe
from django.views import View
from django.views.generic import ListView, TemplateView
from django.views.generic.edit import CreateView, FormView, UpdateView

from coldfront.core.note.models import (Note,
                                        Comment)
from coldfront.core.note.forms import AllocationNoteCreateForm, NoteCreateForm
from coldfront.core.allocation.forms import (AllocationAccountForm,
                                             AllocationAddUserForm,
                                             AllocationAttributeCreateForm,
                                             AllocationAttributeDeleteForm,
                                             AllocationChangeForm,
                                             AllocationChangeNoteForm,
                                             AllocationAttributeChangeForm,
                                             AllocationAttributeUpdateForm,
                                             AllocationForm,
                                             AllocationInvoiceNoteDeleteForm,
                                             AllocationInvoiceUpdateForm,
                                             AllocationRemoveUserForm,
                                             AllocationReviewUserForm,
                                             AllocationSearchForm,
                                             AllocationUpdateForm
                                            #  AllocationNoteCreateForm
                                             )
from coldfront.core.allocation.models import (Allocation,
                                              AllocationPermission,
                                              AllocationAccount,
                                              AllocationAttribute,
                                              AllocationAttributeType,
                                              AllocationChangeRequest,
                                              AllocationChangeStatusChoice,
                                              AllocationAttributeChangeRequest,
                                              AllocationStatusChoice,
                                              AllocationUser,
                                              AllocationUserNote,
                                              AllocationUserStatusChoice)
from coldfront.core.allocation.signals import (allocation_new,
                                               allocation_activate,
                                               allocation_activate_user,
                                               allocation_disable,
                                               allocation_remove_user,
                                               allocation_change_approved,)
from coldfront.core.allocation.utils import (generate_guauge_data_from_usage,
                                             get_user_resources)
from coldfront.core.project.models import (Project, ProjectUser, ProjectPermission,
                                           ProjectUserStatusChoice)
from coldfront.core.resource.models import Resource
from coldfront.core.utils.common import Echo, get_domain_url, import_from_settings
from coldfront.core.utils.mail import send_allocation_admin_email, send_allocation_customer_email

# Create your views here.
class NoteCreateView(LoginRequiredMixin, UserPassesTestMixin, FormView):
    form_class = NoteCreateForm
    # fields = '__all__'
    template_name = 'note/allocation_note_create.html'
    model_type = ''
    object_relation = {"Allocation":Allocation,"Project":Project}


    def object_type(self):
        if(self.kwargs.get('allocation_pk','Project') == "Project"): 
            obj = get_object_or_404(Project, pk=self.kwargs.get('project_pk'))
            self.model_type = 'Allocation'
        else:
            obj = get_object_or_404(Project, pk=self.kwargs.get('project_pk'))
            self.model_type = 'Project'
        return self.model_type, obj
    


    def test_func(self):
        """ UserPassesTestMixin Tests"""


        if(self.kwargs.get('allocation_pk','Project') != "Project"):
            allocation_obj = get_object_or_404(Allocation, pk=self.kwargs.get('allocation_pk'))
            self.model_type = 'Allocation'
        else:
            allocation_obj = get_object_or_404(Project, pk=self.kwargs.get('project_pk'))
            self.model_type = 'Project'
        model_obj = get_object_or_404(Allocation, pk=self.kwargs.get('allocation_pk'))
        if self.request.user.is_superuser:
            return True
        
        else:
            messages.error(
                self.request, 'You do not have permission to add allocation notes.')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            model_obj = get_object_or_404(Allocation, pk=self.kwargs.get('allocation_pk'))
            context['allocation'] = model_obj
            context['type'] = "Allocation"
        except:
            model_obj = get_object_or_404(Project, pk=self.kwargs.get('project_pk'))
            context['type'] = "Project"
        return context


    def get_form(self, form_class=form_class):
        """Return an instance of the form to be used in this view."""
        if(self.model_type == "Allocation"):
            return form_class(self.kwargs.get('allocation_pk'),  **self.get_form_kwargs())
        if(self.model_type == "Project"):
            return form_class(self.kwargs.get('allocation_pk'),  **self.get_form_kwargs())

    
    def form_valid(self, form) -> HttpResponse:
        obj = form
        object_relation = {"Allocation":Allocation,"Project":Project}
        object_name_as_lowercase_string = self.object_type.lower()
        model_obj = get_object_or_404(object_relation[self.object_type], pk=self.kwargs.get(object_name_as_lowercase_string+'_pk'))
        form_complete = NoteCreateForm(model_obj.pk,self.request.POST,initial = {"author":self.request.user,"message":obj.data['message']})
        if form_complete.is_valid():
            form_data = form_complete.cleaned_data
            if(object_name_as_lowercase_string == "allocation"):
                new_note_obj = Note.objects.create(
                    title = form_data["title"],
                    allocation = model_obj,
                    message = form_data["message"],
                    tags = form_data["tags"],
                    author = self.request.user,
                )
            else:
                new_note_obj = Note.objects.create(
                    title = form_data["title"],
                    project = model_obj,
                    message = form_data["message"],
                    tags = form_data["tags"],
                    author = self.request.user,
                )


        
        self.pk_hold = new_note_obj.pk
        self.object = obj

        return super().form_valid(form)
    
    
    def get_success_url(self):
        # if()
        return reverse('notes-detail', kwargs={'pk': self.pk_hold})



class AllocationNoteDownloadView(LoginRequiredMixin, UserPassesTestMixin, ListView):
      def test_func(self):
        """ UserPassesTestMixin Tests"""
        if self.request.user.is_superuser:
            return True

        model_obj = get_object_or_404(Allocation, pk=self.kwargs.get('pk'))

        if model_obj.project.pi == self.request.user:
            return True

        if model_obj.projectuser_set.filter(user=self.request.user, role__name='Manager', status__name='Active').exists():
            return True

        messages.error(self.request, 'You do not have permission to download all notes.')

      def get(self, request, pk):  
          header = [
              "Comment",
              "Administrator",
              "Created By",
              "Last Modified"
          ]  
          rows = []
          allocation_obj = get_object_or_404(Allocation, pk=self.kwargs.get('pk'))

          notes = allocation_obj.allocationusernote_set.all()

          for note in notes:
              row = [
                  note.message,
                  note.author,
                  note.tags,
                  note.modified
              ]  
              rows.append(row)
          rows.insert(0, header)
          pseudo_buffer = Echo()
          writer = csv.writer(pseudo_buffer)
          response = StreamingHttpResponse((writer.writerow(row) for row in rows),
                                              content_type="text/csv")
          response['Content-Disposition'] = 'attachment; filename="notes.csv"'
          return response
      
class CommentCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = Comment
    fields = '__all__'
    template_name = 'note/comment_create.html'

    def test_func(self):
        """ UserPassesTestMixin Tests"""
        if self.request.user.is_superuser:
            return True
        messages.error( self.request, 'You do not have permission to add allocation notes.')
        return False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pk = self.kwargs.get('pk')
        note = get_object_or_404(Note, pk=pk)
        context['note'] = note
        return context

    def get_initial(self):
        initial = super().get_initial()
        pk = self.kwargs.get('pk')
        note_ = get_object_or_404(Note, pk=pk)
        author = self.request.user
        initial['note_'] = note_
        initial['author'] = author
        return initial

    def get_form(self, form_class=None):
        """Return an instance of the form to be used in this view."""
        form = super().get_form(form_class)
        form.fields['note_'].widget = forms.HiddenInput()
        form.fields['author'].widget = forms.HiddenInput()
        form.order_fields([ 'note_', 'author', 'note', 'is_private' ])
        return form

    def get_success_url(self):
        return reverse('note-detail', kwargs={'pk': self.kwargs.get('pk')})

class AllocationNoteDetailView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    model = Note
    template_name = 'note/allocation_note_detail.html'
    context_object_name = 'note'

    def test_func(self):
        """ UserPassesTestMixin Tests"""
        pk = self.kwargs.get('pk')
        allocation_obj = get_object_or_404(Note, pk=pk)

        # if self.request.user.has_perm('allocation.can_view_all_allocations'):
        #     return True
        return True

        # return allocation_obj.has_perm(self.request.user, AllocationPermission.USER)
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pk = self.kwargs.get('pk')
        # allocation_obj = get_object_or_404(Allocation, pk=pk)
        note_obj = get_object_or_404(Note, pk=pk)
        context["note"] = note_obj

        comments = []

        for comment in note_obj.allocation.allocationusernote_set.all():
            comments.append(comment)
        
        context["comments"] = comments

        return context
        # # set visible usage attributes
        # alloc_attr_set = allocation_obj.get_attribute_set(self.request.user)
        # attributes_with_usage = [a for a in alloc_attr_set if hasattr(a, 'allocationattributeusage')]
        # attributes = alloc_attr_set

    