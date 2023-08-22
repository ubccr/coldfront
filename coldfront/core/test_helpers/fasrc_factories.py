import factory
from factory import SubFactory
from factory.django import DjangoModelFactory
from ifxbilling.models import Product, Facility
from ifxuser.models import Organization, OrgRelation, UserAffiliation

from coldfront.core.project.models import Project
from coldfront.plugins.ifx.models import ProductResource, ProjectOrganization
from coldfront.core.test_helpers.factories import (
    UserFactory,
    ProjectFactory,
    ResourceFactory,
    ProjectUserFactory,
)

class FacilityFactory(DjangoModelFactory):
    """Factory for Facility model"""
    class Meta:
        model = Facility
        django_get_or_create = ('facility_name',)

    name = 'HPC Storage'
    application_username = 'coldfront'
    credit_code = 123456
    invoice_prefix = 'RC'
    object_code = 123456
    billing_record_template = 'plugins/ifx/billing_record_summary.html'


class ProductFactory(DjangoModelFactory):
    """Factory for Product model"""
    class Meta:
        model = Product
        django_get_or_create = ('product_name',)

    product_name = factory.Faker('word')
    description = factory.Faker('paragraph')
    billing_calculator = 'coldfront.plugins.ifx.calculator.NewColdfrontBillingCalculator'
    facility = SubFactory(FacilityFactory)
    billable = True


class ProductResourceFactory(DjangoModelFactory):
    """Factory for ProductResource model"""
    class Meta:
        model = ProductResource

    product =  SubFactory(ProductFactory)
    resource = SubFactory(ResourceFactory)

class OrganizationFactory(DjangoModelFactory):
    """Factory for Organization model"""
    class Meta:
        model = Organization
        django_get_or_create = ('name',)

    name = factory.Faker('word')
    rank = 'school'
    org_tree = 'Harvard'

class ProjectOrganizationFactory(DjangoModelFactory):
    """Factory for ProjectOrganization model"""
    class Meta:
        model = ProjectOrganization

    project = SubFactory(ProjectFactory)
    organization = SubFactory(OrganizationFactory, name='project_title')

class OrgRelationFactory(DjangoModelFactory):
    """Factory for Department model"""
    class Meta:
        model = OrgRelation
    parent=SubFactory(OrganizationFactory)
    child=SubFactory(OrganizationFactory)

class UserAffiliationFactory(DjangoModelFactory):
    """Factory for UserAffiliation model"""
    class Meta:
        model = UserAffiliation
    user=SubFactory(UserFactory)
    organization=SubFactory(OrganizationFactory)
    role='user'
    active=True

def setup_departments(test_case):
    test_case.dept_manager_user = UserFactory(
        username='eostrom',
        first_name='Elinor',
        last_name='Ostrom',
        full_name='Elinor Ostrom',
    )

    test_case.school = OrganizationFactory(
        name='School of Maths and Sciences',
        rank='school',
        org_tree='Research Computing Storage Billing',
    )
    test_case.dept = OrganizationFactory(
        name='Computational Chemistry',
        rank='department',
        org_tree='Research Computing Storage Billing',
    )


    test_case.dept_member_user = UserFactory(
        username='jdoe',
        first_name='John',
        last_name='Doe',
        full_name='John Doe',
    )
    ProjectFactory()
    for project in Project.objects.all():
        project_title = project.title
        org = OrganizationFactory(
            name=project_title, rank='lab', org_tree='Harvard'
        )
        ProjectOrganizationFactory(project=project, organization=org)

        OrgRelationFactory(parent=test_case.school, child=org)

    dept2_proj = ProjectFactory(pi=test_case.dept_member_user)
    dept2_proj_org = OrganizationFactory(
        name=dept2_proj.title, rank='lab', org_tree='Harvard'
    )
    ProjectOrganizationFactory(project=dept2_proj, organization=dept2_proj_org)
    OrgRelationFactory(parent=test_case.dept, child=dept2_proj_org)
    ProjectUserFactory(project=dept2_proj, user=test_case.dept_member_user)
    # set up UserAffiliations
    UserAffiliationFactory(
        user=test_case.dept_manager_user,
        organization=test_case.school,
        role='approver',
        active=True,
    )
    UserAffiliationFactory(
        user=test_case.dept_member_user,
        organization=test_case.dept,
        role='user',
        active=True,
    )
