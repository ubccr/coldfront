from django import forms
from django.contrib import messages
from django.views.generic import ListView
from django.db.models.query import QuerySet
from django.shortcuts import get_object_or_404
from django.views.generic.edit import CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin

def produce_filter_parameter(key, value):
    if isinstance(value, list):
        return ''.join([f'{key}={ele}&' for ele in value])
    if isinstance(value, QuerySet):
        return ''.join([f'{key}={ele.pk}&' for ele in value])
    if hasattr(value, 'pk'):
        return f'{key}={value.pk}&'
    return f'{key}={value}&'


class ColdfrontListView(LoginRequiredMixin, ListView):
    """A ListView with definitions standard to complex ListView implementations in ColdFront
    """

    def return_order(self):
        """standardize the method for the 'order_by' value used in get_queryset"""
        order_by = self.request.GET.get('order_by', 'id')
        direction = self.request.GET.get('direction', '')
        if order_by != 'name':
            direction = '-' if direction == 'des' else ''
            order_by = direction + order_by
        return order_by

    def filter_parameters(self, SearchFormClass):
        search_form = SearchFormClass(self.request.GET)
        if search_form.is_valid():
            data = search_form.cleaned_data
            filter_parameters = ''
            for key, value in data.items():
                if value:
                    filter_parameters += produce_filter_parameter(key, value)
        else:
            filter_parameters = None
            search_form = SearchFormClass()
        order_by = self.request.GET.get('order_by')
        if order_by:
            direction = self.request.GET.get('direction')
            filter_parameters_with_order_by = filter_parameters + \
                f'order_by={order_by}&direction={direction}&'
        else:
            filter_parameters_with_order_by = filter_parameters
        return search_form, filter_parameters, filter_parameters_with_order_by

    def get_context_data(self, SearchFormClass=None, **kwargs):
        context = super().get_context_data(**kwargs)
        count = self.get_queryset().count()
        context['count'] = count

        search_form, filter_parameters, filter_parameters_with_order_by = self.filter_parameters(SearchFormClass)
        if filter_parameters:
            context['expand_accordion'] = 'show'

        context['search_form'] = search_form
        context['filter_parameters'] = filter_parameters
        context['filter_parameters_with_order_by'] = filter_parameters_with_order_by

        return context


class NoteUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    template_name = 'note_update.html'
    fields = ('is_private', 'note',)

    def test_func(self):
        """ UserPassesTestMixin Tests"""
        note_obj = get_object_or_404(self.model, pk=self.kwargs.get('pk'))
        is_author = self.request.user == note_obj.author
        if self.request.user.is_superuser or is_author:
            return True
        messages.error(self.request, 'You do not have permission to change this note.')
        return False


class NoteCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    template_name = 'note_create.html'
    fields = '__all__'

    def test_func(self):
        """ UserPassesTestMixin Tests"""
        if self.request.user.is_superuser:
            return True
        messages.error(
            self.request, 'You do not have permission to add allocation notes.')
        return False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pk = self.kwargs.get('pk')
        obj = get_object_or_404(self.object_model, pk=pk)
        context['object'] = obj
        return context

    def get_initial(self):
        initial = super().get_initial()
        pk = self.kwargs.get('pk')
        obj = get_object_or_404(self.object_model, pk=pk)
        author = self.request.user
        initial[self.form_obj] = obj
        initial['author'] = author
        return initial

    def get_form(self, form_class=None):
        """Return an instance of the form to be used in this view."""
        form = super().get_form(form_class)
        form.fields[self.form_obj].widget = forms.HiddenInput()
        form.fields['author'].widget = forms.HiddenInput()
        form.order_fields([ self.form_obj, 'author', 'note', 'is_private' ])
        return form
