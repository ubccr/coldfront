from django import forms
from django.template.loader import render_to_string

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Field, Layout, Submit, HTML, Row, Column, Fieldset, Reset, LayoutObject, Div
from crispy_forms.bootstrap import InlineRadios, FormActions, PrependedText, AccordionGroup, Accordion

from coldfront.core.project.models import ProjectTypeChoice, ProjectStatusChoice
from coldfront.core.allocation.models import AllocationStatusChoice, AllocationAttributeType
from coldfront.core.resource.models import Resource, ResourceType


class AllocationAttributeFormSetHelper(FormHelper):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.use_custom_control = False 
        self.layout = Layout(
            Div(
                Div(
                    Row(
                        Column('allocationattribute__name'),
                        Column('allocationattribute__value'),
                    ),
                    Row(
                        Column('allocationattribute__has_usage'),
                        Column('allocationattribute__equality'),
                        Column('allocationattribute__usage'),
                        Column('allocationattribute__usage_format')
                    ),
                    css_class='card-body'
                ),
                css_class='card mb-3'
            )
        )


class AllocationAttributeSearchForm(forms.Form):
    EQUALITY_CHOICES = (
        ('lt', '<'),
        ('gt', '>')
    )
    FORMAT_CHOICES = (
        ('whole', '.00'),
        ('percent', '%')
    )
    YES_NO_CHOICES = (
        (1, 'Yes'),
        (0, 'No')
    )

    allocationattribute__name = forms.ModelChoiceField(
        label='Allocation Attribute Name',
        queryset=AllocationAttributeType.objects.none() ,
        help_text=(
            f'To display the list of allocation attributes at least one resource must be selected.'
        ),
        required=False,
    )
    allocationattribute__value = forms.CharField(
        label='Allocation Attribute Value',
        max_length=50,
        required=False
    )
    allocationattribute__has_usage = forms.ChoiceField(
        initial=0, label='Has usage', choices=YES_NO_CHOICES, required=False,
    )
    allocationattribute__equality = forms.ChoiceField(
        label='Equality', choices=EQUALITY_CHOICES, required=False
    )
    allocationattribute__usage = forms.FloatField(label='Usage' , required=False)
    allocationattribute__usage_format = forms.ChoiceField(
        label='Format', choices=FORMAT_CHOICES, required=False
    )

    def __init__(self, *args, resources=None, **kwargs):
        super().__init__(*args, **kwargs)
        if resources:
            self.fields['allocationattribute__name'].queryset = AllocationAttributeType.objects.prefetch_related(
                'attribute_type'
            ).filter(linked_resources__in=resources).distinct().order_by('name')
        else:
            self.fields['allocationattribute__name'].queryset = AllocationAttributeType.objects.none() 


class SearchForm(forms.Form):
    only_search_projects = forms.BooleanField(required=False)

    display__project__id = forms.BooleanField(required=False)

    project__title = forms.CharField(
        label='Project Title Contains', max_length=100, required=False
    )
    display__project__title = forms.BooleanField(required=False)

    project__description = forms.CharField(
        label='Project Description Contains', max_length=100, required=False
    )
    display__project__description = forms.BooleanField(required=False)

    project__pi__username = forms.CharField(
        label='PI Username Contains', max_length=25, required=False
    )
    display__project__pi__username = forms.BooleanField(required=False)

    project__requestor__username = forms.CharField(
        label='Requestor Username Contains', max_length=25, required=False
    )
    display__project__requestor__username = forms.BooleanField(required=False)

    project__status__name = forms.ModelMultipleChoiceField(
        label='Project Status',
        queryset=ProjectStatusChoice.objects.all().order_by('name'),
        required=False
    )
    display__project__status__name = forms.BooleanField(required=False)

    project__type__name = forms.ModelMultipleChoiceField(
        label='Project Type',
        queryset=ProjectTypeChoice.objects.all().order_by('name'),
        required=False
    )
    display__project__type__name = forms.BooleanField(required=False)

    project__class_number = forms.CharField(
        label='Class Number', max_length=25, required=False
    )
    display__project__class_number = forms.BooleanField(required=False)

    display__project__users = forms.BooleanField(
        required=False, help_text='Active users. Ignored if "only search projects" is not selected'
    )

    display__project__total_users = forms.BooleanField(required=False, help_text='Active users')

    display__allocation__id = forms.BooleanField(required=False)

    allocation__status__name = forms.ModelMultipleChoiceField(
        label='Allocation Status',
        queryset=AllocationStatusChoice.objects.all().order_by('name'),
        required=False
    )
    display__allocation__status__name = forms.BooleanField(required=False)

    display__allocation__users = forms.BooleanField(required=False, help_text='Active users')

    display__allocation__total_users = forms.BooleanField(required=False, help_text='Active users')

    resources__name = forms.ModelMultipleChoiceField(
        label='Resource Name',
        help_text= (
            f'The selection of allocation attributes is only updated of after the search form is '
            f'submitted.'
        ),
        queryset=Resource.objects.filter(is_allocatable=True).order_by('name'),
        required=False
    )
    display__resources__name = forms.BooleanField(required=False)

    resources__resource_type__name = forms.ModelMultipleChoiceField(
        label='Resource Type',
        queryset=ResourceType.objects.all().order_by('name'),
        required=False
    )
    display__resources__resource_type__name = forms.BooleanField(required=False)

    allocationattribute_form = AllocationAttributeSearchForm()
    allocationattribute_helper = AllocationAttributeFormSetHelper()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper(self)
        self.helper.use_custom_control = False 
        self.helper.layout = Layout(
            Accordion(
                AccordionGroup('Projects',
                    'only_search_projects',
                    'project__title',
                    'project__description',
                    'project__pi__username',
                    'project__requestor__username',
                    'project__status__name',
                    'project__type__name',
                    'project__class_number',
                    'display__project__id',
                    'display__project__title',
                    'display__project__description',
                    'display__project__pi__username',
                    'display__project__requestor__username',
                    'display__project__status__name',
                    'display__project__type__name',
                    'display__project__class_number',
                    'display__project__users',
                    'display__project__total_users',
                ),
            ),
            Accordion(
                AccordionGroup('Allocations',
                    'allocation__status__name',
                    'display__allocation__id',
                    'display__allocation__status__name',
                    'display__allocation__users',
                    'display__allocation__total_users'
                )
            ),
            Accordion(
                AccordionGroup('Resources',
                    'resources__name',
                    'resources__resource_type__name',
                    'display__resources__name',
                    'display__resources__resource_type__name'
                )
            ),
            Accordion(
                AccordionGroup('Allocation Attributes',
                    Formset('allocationattribute_form', 'allocationattribute_helper', label='allocationattribute_formset'),
                    HTML(
                        '<button id="id_formset_add_allocation_attribute_button" type="button" class="btn btn-primary">Add Allocation Attribute</button>'
                    )
                )
            ),
            FormActions(
                Submit('submit', 'Search'),
                Reset('reset', 'Reset')
            ),
        )

class Formset(LayoutObject):
    template = "advanced_exporting/formset.html"

    def __init__(self, formset_context_name, helper_context_name=None,
                 template=None, label=None):

        self.formset_context_name = formset_context_name
        self.helper_context_name = helper_context_name
        self.label = label

        # crispy_forms/layout.py:302 requires us to have a fields property
        self.fields = []

        # Overrides class variable with an instance level variable
        if template:
            self.template = template

    def render(self, form, form_style, context, **kwargs):
        formset = context.get(self.formset_context_name)
        helper = context.get(self.helper_context_name)
        # closes form prematurely if this isn't explicitly stated
        if helper:
            helper.form_tag = False

        context.update({'formset': formset, 'helper': helper, 'label': self.label})
        return render_to_string(self.template, context.flatten())
