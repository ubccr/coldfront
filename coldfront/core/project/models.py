import datetime
import textwrap
from enum import Enum

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import MinLengthValidator
from django.db import models
from ast import literal_eval
from coldfront.core.utils.validate import AttributeValidator
from model_utils.models import TimeStampedModel
from simple_history.models import HistoricalRecords

from coldfront.core.field_of_science.models import FieldOfScience
from coldfront.core.utils.common import import_from_settings

PROJECT_ENABLE_PROJECT_REVIEW = import_from_settings('PROJECT_ENABLE_PROJECT_REVIEW', False)
PROJECT_DAYS_TO_REVIEW_AFTER_EXPIRING = import_from_settings(
    'PROJECT_DAYS_TO_REVIEW_AFTER_EXPIRING', 60)
PROJECT_DAYS_TO_REVIEW_BEFORE_EXPIRING = import_from_settings(
    'PROJECT_DAYS_TO_REVIEW_BEFORE_EXPIRING', 30)

class ProjectPermission(Enum):
    """ A project permission stores the user, manager, pi, and update fields of a project. """

    USER = 'user'
    MANAGER = 'manager'
    PI = 'pi'
    UPDATE = 'update'

class ProjectStatusChoice(TimeStampedModel):
    """ A project status choice indicates the status of the project. Examples include Active, Archived, and New. 
    
    Attributes:
        name (str): name of project status choice
    """
    class Meta:
        ordering = ('name',)

    class ProjectStatusChoiceManager(models.Manager):
        def get_by_natural_key(self, name):
            return self.get(name=name)

    name = models.CharField(max_length=64, unique=True)
    objects = ProjectStatusChoiceManager()

    def __str__(self):
        return self.name

    def natural_key(self):
        return (self.name,)


class ProjectTypeChoice(TimeStampedModel):
    name = models.CharField(max_length=64)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ('name',)


class Project(TimeStampedModel):
    """ A project is a container that includes users, allocations, publications, grants, and other research output. 
    
    Attributes:
        title (str): name of the project
        pi (User): represents the User object of the project's PI
        description (str): description of the project
        field_of_science (FieldOfScience): represents the field of science for this project
        status (ProjectStatusChoice): represents the ProjectStatusChoice of this project
        force_review (bool): indicates whether or not to force a review for the project
        requires_review (bool): indicates whether or not the project requires review
    """
    class Meta:
        ordering = ['title']
        # unique_together = ('title', 'pi')

        permissions = (
            ("can_view_all_projects", "Can view all projects"),
            ("can_review_pending_project_reviews", "Can review pending project reviews"),
        )

    class ProjectManager(models.Manager):
        def get_by_natural_key(self, title, pi_username):
            return self.get(title=title, pi__username=pi_username)

    DEFAULT_DESCRIPTION = ''
    DESCRIPTION_HELP_TEXT = """
Please provide a brief description or abstract about your project including any applications or
workflows you intend to use, and how you primarily intend to use the system, including if PHI will
be stored. Please include your area of research and your department. If this is for a class please
put the approximate class size.
"""

    title = models.CharField(max_length=255,)
    pi = models.ForeignKey(User, on_delete=models.CASCADE,)
    pi_username = models.CharField(
        verbose_name="PI Username",
        max_length=20,
        blank=True,
        help_text="""
Required if you will not be the PI of this project. Only faculty and staff can be the PI. They are
required to log onto the site at least once before they can be added.
"""
    )
    requestor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='requestor_user')
    description = models.TextField(
        default=DEFAULT_DESCRIPTION,
        help_text=DESCRIPTION_HELP_TEXT,
        validators=[
            MinLengthValidator(
                10,
                'The project description must be > 10 characters.',
            )
        ],
    )

    slurm_account_name = models.CharField(
        max_length=15,
        blank=True,
        null=True,
        unique=True
    )
    field_of_science = models.ForeignKey(FieldOfScience, on_delete=models.CASCADE, default=FieldOfScience.DEFAULT_PK)
    type = models.ForeignKey(
        ProjectTypeChoice,
        on_delete=models.CASCADE,
        help_text="This cannot be changed once your project is submitted. Class projects expire at the end of every semester. Research projects expire once a year."
    )
    class_number = models.CharField(max_length=25, blank=True, null=True)
    private = models.BooleanField(
        default=False,
        help_text="A private project will not show up in the PI search results if someone searchs for you/your PI."
    )
    status = models.ForeignKey(ProjectStatusChoice, on_delete=models.CASCADE)
    force_review = models.BooleanField(default=False)
    requires_review = models.BooleanField(default=True)
    end_date = models.DateField()
    max_managers = models.IntegerField()
    history = HistoricalRecords()
    objects = ProjectManager()

    def clean(self):
        """ Validates the project and raises errors if the project is invalid. """

        if 'Auto-Import Project'.lower() in self.title.lower():
            raise ValidationError('You must update the project title. You cannot have "Auto-Import Project" in the title.')

    @property
    def last_project_review(self):
        """
        Returns:
            ProjectReview: the last project review that was created for this project
        """

        if self.projectreview_set.exists():
            return self.projectreview_set.order_by('-created')[0]
        else:
            return None

    @property
    def latest_grant(self):
        """
        Returns:
            Grant: the most recent grant for this project, or None if there are no grants
        """

        if self.grant_set.exists():
            return self.grant_set.order_by('-modified')[0]
        else:
            return None

    @property
    def latest_publication(self):
        """
        Returns:
            Publication: the most recent publication for this project, or None if there are no publications
        """

        if self.publication_set.exists():
            return self.publication_set.order_by('-created')[0]
        else:
            return None

    @property
    def needs_review(self):
        """
        Returns:
            bool: whether or not the project needs review
        """

        if self.status.name in ['Archived', 'Expired', 'Review Pending']:
            return False

        if self.force_review is True:
            return True

        return False

    @property
    def can_be_reviewed(self):
        if self.status.name in ['Archived', 'Denied', 'Review Pending']:
            return False

        if self.force_review is True:
            return False

        if not PROJECT_ENABLE_PROJECT_REVIEW:
            return False

        if self.requires_review is False:
            return False

        if self.status.name == 'Active' and self.expires_in <= PROJECT_DAYS_TO_REVIEW_BEFORE_EXPIRING:
            return True
        
        if self.status.name == 'Expired' and PROJECT_DAYS_TO_REVIEW_AFTER_EXPIRING < 0:
            return True

        if self.status.name == 'Expired' and self.expires_in >= -PROJECT_DAYS_TO_REVIEW_AFTER_EXPIRING:
            return True

        return False
    
    def user_permissions(self, user, permission=None):
        """
        Params:
            user (User): represents the user whose permissions are to be retrieved

        Returns:
            list[ProjectPermission]: a list of the user's permissions for the project
        """

        if user.is_superuser:
            return list(ProjectPermission)

        permissions = [ProjectPermission.USER]
        user_conditions = (models.Q(status__name__in=('Active', 'New')) & models.Q(user=user))
        if not self.projectuser_set.filter(user_conditions).exists():
            if permission and user.has_perm(permission):
                permissions.append(ProjectPermission.MANAGER)
            else:
                return []

        if self.projectuser_set.filter(user_conditions & models.Q(role__name='Manager')).exists():
            permissions.append(ProjectPermission.MANAGER)

        if self.projectuser_set.filter(user_conditions & models.Q(project__pi_id=user.id)).exists():
            permissions.append(ProjectPermission.PI)

        if ProjectPermission.MANAGER in permissions or ProjectPermission.MANAGER in permissions:
            permissions.append(ProjectPermission.UPDATE)

        return permissions

    def has_perm(self, user, perm, addtl_perm=None):
        """
        Params:
            user (User): user to check permissions for
            perm (ProjectPermission): permission to check for in user's list

        Returns:
            bool: whether or not the user has the specified permission
        """

        perms = self.user_permissions(user, addtl_perm)
        return perm in perms

    @property
    def expires_in(self):
        return (self.end_date - datetime.date.today()).days

    @property
    def list_of_manager_usernames(self):
        project_managers = self.projectuser_set.filter(
            role=ProjectUserRoleChoice.objects.get(name='Manager')
        )
        return [manager.user.username for manager in project_managers]
    
    def get_list_of_resources_with_slurm_accounts(self, user):
        resources = set()
        allocations = self.allocation_set.filter(
            status__name__in=['Active', 'Renewal Requested', ],
            allocationuser__user=user,
            allocationuser__status__name='Active'
        )
        for allocation in allocations:
            resource = allocation.get_parent_resource
            slurm_cluster = None
            if resource.parent_resource is not None:
                slurm_cluster = resource.parent_resource.get_attribute('slurm_cluster')
            if slurm_cluster:
                resources.add(allocation.get_parent_resource.name)

        return list(resources)

    def get_current_num_managers(self):
        return self.projectuser_set.filter(
            role=ProjectUserRoleChoice.objects.get(name='Manager'),
            status=ProjectUserStatusChoice.objects.get(name='Active'),
            ).count()

    def check_exceeds_max_managers(self, num_added_managers=0):
        """
        Checks if the number of added managers exceeds the max allowed managers.
        """
        return (self.get_current_num_managers() + num_added_managers) > self.max_managers

    def __str__(self):
        return self.title

    def natural_key(self):
        return (self.title,) + self.pi.natural_key()

class ProjectAdminComment(TimeStampedModel):
    """ A project admin comment is a comment that an admin can make on a project. 
    
    Attributes:
        project (Project): links the project the comment is from to the comment
        author (User): represents the admin who authored the comment
        comment (str): text input from the project admin containing the comment
    """

    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    comment = models.TextField()

    def __str__(self):
        return self.comment

class ProjectUserMessage(TimeStampedModel):
    """ A project user message is a message sent to a user in a project. 
    
    Attributes:
        project (Project): links the project the message is from to the message
        author (User): represents the user who authored the message
        is_private (bool): indicates whether or not the message is private
        message (str): text input from the user containing the message
    """

    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    is_private = models.BooleanField(default=True)
    message = models.TextField()

    def __str__(self):
        return self.message

class ProjectReviewStatusChoice(TimeStampedModel):
    """ A project review status choice is an option a user can choose when setting a project's status. Examples include Completed and Pending.
    
    Attributes:
        name (str): name of the status choice
    """

    name = models.CharField(max_length=64)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name', ]

class ProjectReview(TimeStampedModel):
    """ A project review is what a user submits to their PI when their project status is Pending. 
    
    Attributes:
        project (Project): links the project to its review
        status (ProjectReviewStatusChoice): links the project review to its status
        reason_for_not_updating_project (str): text input from the user indicating why the project was not updated
    """

    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    status = models.ForeignKey(ProjectReviewStatusChoice, on_delete=models.CASCADE, verbose_name='Status')
    project_updates = models.TextField(blank=True, null=True)
    allocation_renewals = models.TextField(blank=True, null=True)
    history = HistoricalRecords()

class ProjectUserRoleChoice(TimeStampedModel):
    """ A project user role choice is an option a PI, manager, or admin has while selecting a user's role. Examples include Manager and User.
    
    Attributes:
        name (str): name of the user role choice  
    """

    class Meta:
        ordering = ['name', ]

    class ProjectUserRoleChoiceManager(models.Manager):
        def get_by_natural_key(self, name):
            return self.get(name=name)

    name = models.CharField(max_length=64, unique=True)
    objects = ProjectUserRoleChoiceManager()

    def __str__(self):
        return self.name

    def natural_key(self):
        return (self.name,)

class ProjectUserStatusChoice(TimeStampedModel):
    """ A project user status choice indicates the status of a project user. Examples include Active, Pending, and Denied.
    
    Attributes:
        name (str): name of the project user status choice
    """
    class Meta:
        ordering = ['name', ]

    class ProjectUserStatusChoiceManager(models.Manager):
        def get_by_natural_key(self, name):
            return self.get(name=name)

    name = models.CharField(max_length=64, unique=True)
    objects = ProjectUserStatusChoiceManager()

    def __str__(self):
        return self.name

    def natural_key(self):
        return (self.name,)

class ProjectUser(TimeStampedModel):
    """ A project user represents a user on the project.
    
    Attributes:
        user (User): represents the User object of the project user
        project (Project): links user to its project
        role (ProjectUserRoleChoice): links the project user role choice to the user
        status (ProjectUserStatusChoice): links the project user status choice to the user
        enable_notifications (bool): indicates whether or not the user should enable notifications
    """

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    role = models.ForeignKey(ProjectUserRoleChoice, on_delete=models.CASCADE)
    status = models.ForeignKey(ProjectUserStatusChoice, on_delete=models.CASCADE, verbose_name='Status')
    enable_notifications = models.BooleanField(default=True)
    history = HistoricalRecords()

    def __str__(self):
        return '%s %s (%s)' % (self.user.first_name, self.user.last_name, self.user.username)

    class Meta:
        unique_together = ('user', 'project')
        verbose_name_plural = "Project User Status"

class AttributeType(TimeStampedModel):
    """ An attribute type indicates the data type of the attribute. Examples include Date, Float, Int, Text, and Yes/No. 
    
    Attributes:
        name (str): name of attribute data type
    """
    
    name = models.CharField(max_length=64)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name', ]

class ProjectAttributeType(TimeStampedModel):
    """ A project attribute type indicates the type of the attribute. Examples include Project ID and Account Number. 
    
    Attributes:
        attribute_type (AttributeType): indicates the data type of the attribute
        name (str): name of project attribute type
        has_usage (bool): indicates whether or not the attribute type has usage
        is_required (bool): indicates whether or not the attribute is required
        is_unique (bool): indicates whether or not the value is unique
        is_private (bool): indicates whether or not the attribute type is private
        is_changeable (bool): indicates whether or not the attribute type is changeable
    """

    attribute_type = models.ForeignKey(AttributeType, on_delete=models.CASCADE)
    name = models.CharField(max_length=50)
    has_usage = models.BooleanField(default=False)
    is_required = models.BooleanField(default=False)
    is_unique = models.BooleanField(default=False)
    is_private = models.BooleanField(default=True)
    is_changeable = models.BooleanField(default=False)
    history = HistoricalRecords()

    def __str__(self):
        return '%s (%s)' % (self.name, self.attribute_type.name)

    def __repr__(self) -> str:
        return str(self)

    class Meta:
        ordering = ['name', ]

class ProjectAttribute(TimeStampedModel):
    """ A project attribute class links a project attribute type and a project. 
    
    Attributes:
        proj_attr_type (ProjectAttributeType): project attribute type to link
        project (Project): project to link
        value (str): value of the project attribute
    """

    proj_attr_type = models.ForeignKey(ProjectAttributeType, on_delete=models.CASCADE)
    project = models.ForeignKey(Project, on_delete=models.CASCADE)

    value = models.CharField(max_length=128)
    history = HistoricalRecords()

    def save(self, *args, **kwargs):
        """ Saves the project attribute. """
        super().save(*args, **kwargs)
        if self.proj_attr_type.has_usage and not ProjectAttributeUsage.objects.filter(project_attribute=self).exists():
            ProjectAttributeUsage.objects.create(
                project_attribute=self)

    def clean(self):
        """ Validates the project and raises errors if the project is invalid. """
        if self.proj_attr_type.is_unique and self.project.projectattribute_set.filter(proj_attr_type=self.proj_attr_type).exists():
            raise ValidationError("'{}' attribute already exists for this project.".format(
                self.proj_attr_type))

        expected_value_type = self.proj_attr_type.attribute_type.name.strip()

        validator = AttributeValidator(self.value)

        if expected_value_type == "Int":
            validator.validate_int()
        elif expected_value_type == "Float":
            validator.validate_float()
        elif expected_value_type == "Yes/No":
            validator.validate_yes_no()
        elif expected_value_type == "Date":
            validator.validate_date()

    def __str__(self):
        return '%s' % (self.proj_attr_type.name)

class ProjectAttributeUsage(TimeStampedModel):
    """ Project attribute usage indicates the usage of a project attribute. 
    
    Attributes:
        project_attribute (ProjectAttribute): links the usage to its project attribute
        value (float): usage value of the project attribute
    """

    project_attribute = models.OneToOneField(
        ProjectAttribute, on_delete=models.CASCADE, primary_key=True)
    value = models.FloatField(default=0)
    history = HistoricalRecords()

    def __str__(self):
        return '{}: {}'.format(self.project_attribute.proj_attr_type.name, self.value)

class ProjectAdminAction(TimeStampedModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    action = models.CharField(max_length=100)


class ProjectDescriptionRecord(TimeStampedModel):
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    description = models.TextField()
