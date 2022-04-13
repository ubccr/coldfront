import sys
import logging
import warnings

from django.db import models
from model_utils.models import TimeStampedModel
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db.models import Q, Max

from coldfront.core.project.models import Project
from django.contrib.auth.models import User
from coldfront.core.user.models import UserProfile
from coldfront.core.utils.common import import_from_settings


ORGANIZATION_USER_DISPLAY_MODE = import_from_settings(
    'ORGANIZATION_USER_DISPLAY_MODE')
ORGANIZATION_USER_DISPLAY_TITLE = import_from_settings(
    'ORGANIZATION_USER_DISPLAY_TITLE')
ORGANIZATION_PROJECT_DISPLAY_MODE = import_from_settings(
    'ORGANIZATION_PROJECT_DISPLAY_MODE')
ORGANIZATION_PI_CAN_EDIT_FOR_PROJECT = import_from_settings(
    'ORGANIZATION_PI_CAN_EDIT_FOR_PROJECT')
ORGANIZATION_PROJECT_DISPLAY_TITLE = import_from_settings(
    'ORGANIZATION_PROJECT_DISPLAY_TITLE')
ORGANIZATION_LDAP_AUTH_POPULATE_USER_ORGANIZATIONS = import_from_settings(
    'ORGANIZATION_LDAP_AUTH_POPULATE_USER_ORGANIZATIONS')
ORGANIZATION_LDAP_USER_ATTRIBUTE = import_from_settings(
    'ORGANIZATION_LDAP_USER_ATTRIBUTE')
ORGANIZATION_LDAP_USER_CREATE_PLACEHOLDERS = import_from_settings(
    'ORGANIZATION_LDAP_USER_CREATE_PLACEHOLDERS')
ORGANIZATION_LDAP_USER_DELETE_MISSING = import_from_settings(
    'ORGANIZATION_LDAP_USER_DELETE_MISSING')

logger = logging.getLogger(__name__)

class OrganizationLevel(TimeStampedModel):
    """This defines the different organization levels.

    Each level has a name, level, and optionally a parent.  The level
    describes where in the hierarchy it is, the higher the value for
    level, the higher (more encompassing) the level.  E.g., an 
    academic setting might have levels defined by:
    40: University
    30: College 
    20: Department
    10: ResearchGroup

    The parent would be NULL for the highest level, and for other
    levels should reference the unique entry at the next highest level.
    """

    name = models.CharField(
                max_length=512, 
                null=True, 
                blank=False, 
                unique=True,
                help_text='The (unique) name of the OrganizationLevel',
            )
    level = models.IntegerField(
                null=False, 
                blank=False, 
                unique=True,
                help_text='The lower this value, the higher this type is in '
                    'the organization.',
            )
    parent = models.OneToOneField(
                'self', 
                on_delete=models.PROTECT,
                null=True, 
                blank=True,
                unique=True,
                help_text='The parent OrganizationLevel for this '
                    'OrganizationLevel, or None for the root '
                    'OrganizationLevel',
            )
    export_to_xdmod = models.BooleanField(
                default=True,
                help_text='If set, this OrganizationLevel will be '
                    'exported to Open XdMod',
            )
    # Disable the validation constraints if true.
    # Intended for temporary use when adding/deleting OrgLevels (see
    # add_organization_level and delete_organization_level methods).
    # Always use accessor disable_validation_checks for getting/setting
    # to make it truly behave as class variable
    _disable_validation_checks=False

    class Meta: #for OrganizationLevel
        ordering = ['-level']
    #end: class OrganizationLevel.Meta

    def __str__(self):
        return self.name
    #end: def __str__

    @classmethod
    def disable_validation_checks(cls, new=None):
        """Accessor/mutator for _disable_validation_checks class data member.

        Because of the 'magic' done by django with class variables of Models,
        we must always use the explicit class name when referring to the
        class variable, otherwise we can end up with instance-like copies.

        To better support this, always use this accessor/mutator for getting or
        setting the value.
        """
        if new is not None:
            OrganizationLevel._disable_validation_checks = new
        return OrganizationLevel._disable_validation_checks
    #end: def disable_validation_checks

    def clean(self):
        """Validation: ensure our parent has a higher level than us

        If we have a parent, make sure it has a higher level than us.
        If we do not have a parent, make sure there are no other rows
        in table. (UNIQUE on parent does not work, as SQL allows multiple
        rows with NULL for an UNIQUE field).

        These checks are ignored if disable_validation_checks is set; 
        this is intended for temporary use in add_organization_level
        and delete_organization_level methods.
        """
        # First, call base class's version
        super().clean()

        # Skip custom validation checks if disable_validation_checks
        if self.disable_validation_checks():
            return

        if self.parent:
            # Has a parent, make sure has higher level than us
            plevel = self.parent.level
            if plevel <= self.level:
                raise ValidationError( 'OrganizationLevel {}, level={} '
                    'has parent {} with lower level {}\n' .format(
                        self, 
                        self.level,
                        self.parent, 
                        plevel))
        else: #if self.parent
            # No parent
            # Are there any other OrganizationLevels
            qset = OrganizationLevel.objects.all()
            if qset:
                #Yes, make sure we are the highest level in table
                maxlevel = list(qset.aggregate(Max('level')).values())[0]
                if maxlevel > self.level:
                    raise ValidationError('OrganizationLevel {}, level={} '
                        'has no parent, but max level={}' .format(
                            self, self.level, maxlevel))
                # And that no other parent-less OrgLevels present
                qset2 = qset.filter(parent__isnull=True)
                if qset2:
                    tmp = [ x.name for x in qset ]
                    tmpstr = ', '.join(tmp)
                    raise ValidationError('OrganizationLevel {}, level={} '
                            'has no parent, but [{}] also parentless'.format(
                                self.name, self.level, tmpstr))
                #end if qset2
            #end if qset
        #end if self.parent
        return
    #end: def clean

    def save(self, *args, **kwargs):
        """Override save() to call full_clean first"""
        self.full_clean()
        return super(OrganizationLevel, self).save(*args, **kwargs)
    #end: def save
                
    @classmethod
    def create_or_update_organization_level_by_name(
            cls, name, level, parent=None, export_to_xdmod=True):
        """Create or update an OrganizationLevel with specified data
        
        We check if an OrganizationLevel with the specified name exists.
        If yes, that OrganizationLevel is updated to match the specified
        fields.  If no, a new OrganizationLevel is created with the 
        specified fields.

        parent can be either an OrganizationLevel, or the name
        of an OrganizationLevel, or None for no parent.

        Returns a triplet (obj, created, changes)
        where
            obj is the new or previously-existing OrganizationLevel
            created is a boolean which is true if a new OrgLevel was created
            changes is a (possibly empty) indicating keyed on fields which
                were updated (if existing object updated), the value is 
                a dictionary with keys 'old' and 'new' giving the old and new
                values.
        """
        created = False
        changes = {}

        # Convert parent to an OrganizationLevel instance
        if parent is None:
            # None is OK
            pass
        elif isinstance(parent, OrganizationLevel):
            # Already an OrganizationLevel, nothing to do
            pass
        elif isinstance(parent, str):
            # Got a string, convert to OrganizationLevel
            pname = parent
            parent = OrganizationLevel.objects.get(name=pname)
        else:
            # Error
            raise ValueError('parent must be None, an OrganizationLevel '
                    'instance, or the name of an OrganizationLevel')
        #end: if parent is None

        # See if OrgLevel exists
        qset = OrganizationLevel.objects.filter(name=name)
        if qset:
            # OrgLevel with name name exists, update as needed
            obj = qset[0]
            
            # Level
            needs2change=False
            old = obj.level
            if old is None:
                if level is not None:
                    needs2change = True
            else:
                if level is None or level != old:
                    needs2change = True
            #end: if old is None
            if needs2change:
                obj.level = level
                obj.save()
                changes['level'] = { 'old':old, 'new':level }

            # Parent
            needs2change=False
            old = obj.parent
            if old is None:
                if parent is not None:
                    needs2change = True
            else:
                if parent is None or parent != old:
                    needs2change = True
            #end: if old is None
            if needs2change:
                obj.parent = parent
                obj.save()
                changes['parent'] = { 'old':old, 'new':parent }

            # Export_to_xdmod
            needs2change=False
            old = obj.export_to_xdmod
            if old is None:
                if export_to_xdmod is not None:
                    needs2change = True
            else:
                if export_to_xdmod is None or export_to_xdmod != old:
                    needs2change = True
            #end: if old is None
            if needs2change:
                obj.export_to_xdmod = export_to_xdmod
                obj.save()
                changes['export_to_xdmod'] = { 'old':old, 'new':export_to_xdmod }

        else: #if qset
            # Need to create a new OrganizationLevel
            created = True
            obj = OrganizationLevel.objects.create(
                    name=name,
                    level=level,
                    parent=parent,
                    export_to_xdmod=export_to_xdmod,
                )
            changes = {
                    'name': { 'old':None, 'new':name },
                    'level': { 'old':None, 'new':level },
                    'parent': { 'old':None, 'new':parent },
                    'export_to_xdmod': { 'old':None, 'new':export_to_xdmod },
                }
        #end: if qset
        return obj, created, changes
    #end: def create_or_update_organization_level_by_name

    @classmethod
    def root_organization_level(cls):
        """Returns the 'root' OrganizationLevel, ie orglevel w/out parent.

        Returns the root OrganizationLevel if found (first found), or
        None if none found.
        """
        qset = OrganizationLevel.objects.filter(parent__isnull=True)
        if bool(qset):
            return qset[0]
        else:
            return None
    #end: def root_organization_level

    def child_organization_level(self):
        """Returns the OrganizationLevel whose parent is self.

        Returns None if no child found.
        """
        qset = OrganizationLevel.objects.filter(parent=self)
        if qset:
            return qset[0]
        else:
            return None
    #end: def child_organization_level

    @classmethod
    def generate_orglevel_hierarchy_list(cls, validate=False):
        """This generates a hierarchical list of OrganizationLevels.

        This will return a list of OrganizationLevels, with the
        first element of the list being the root OrganizationLevel,
        and each successive element being the (unique) child of
        the previous element, until we reach the final, childless
        element.

        When validate is true, we perform some extra checks to ensure
        a valid org level hierarchy, raising an ValidationError exception 
        if issues are found.  If validate is false (default), we assume a 
        valid hierarchy; the returned value will still a 'hierarchy' even 
        if the hierarchy is not valid, but it might not be unique unless
        the hierarchy is valid.
        """
        retval = []

        # Find root element
        qset = OrganizationLevel.objects.filter(parent__isnull=True)
        if not bool(qset):
            # No root organization level was found 
            # Not an error, return empty list
            return retval
        if validate:
            # In validate mode, make sure the root org level is unique
            if len(qset) > 1:
                tmp = [ x.name for x in qset ]
                tmpstr = ', '.join(tmp)
                raise ValidationError('OrganizationLevel hierarchy '
                    'has multiple parentless members: {}'.format(
                        tmp))
        last_orglevel = qset[0]
        retval.append(last_orglevel)

        # Now repeatedly add child of last_orglevel
        while last_orglevel is not None:
            qset = OrganizationLevel.objects.filter(parent=last_orglevel)
            if not bool(qset):
                last_orglevel=None
            else:
                if validate:
                    # Make sure only a single child
                    if len(qset) > 1:
                        raise ValidationError('OrganizationLevel hierarchy '
                            'issue: orglevel={} has multiple children: '
                            '{}'.format(last_orglevel, ', '.join(list(qset))))
                last_orglevel = qset[0]
                retval.append(last_orglevel)

        return retval
    #end: def generate_orglevel_hierarchy_list

    @classmethod
    def validate_orglevel_hierarchy(cls):
        """Perform various validation checks on OrganizationLevel hierarchy.

        This performs various checks to ensure a valid hierarchy of
        OrganizationLevels, regardless of disable_validation_checks setting.

        An empty hierarchy (i.e. no OrganizationLevels defined) is valid.
        Otherwise, it ensures that:
        1) There is a single 'root' OrganizationLevel (i.e. OrgLevel without
        a parent OrgLevel)
        2) There is a single 'leaf' OrganizationLevel (i.e. OrgLevel without 
        a child OrgLevel.  Note root=leaf is valid)
        3) All other (non-root, non-leaf) OrganizationLevel have exactly one
        parent and one child OrganizationLevel
        4) For every OrganizationLevel, the value for its level data member
        is strictly greater than that of its child (if it has a child), and
        strictly less than that of its parent (if it has a parent).
        5) All name data members are unique.

        If any issues found, raises a ValidationError exception.
        It will also produce a warning if disable_validation_checks is not
        set
        """
        if cls.disable_validation_checks():
            logger.warning('OrganizationLevel disable_validation_checks is '
                'set')
            warnings.warn('OrganizationLevel disable_validation_checks is '
                'set')

        all_org_levels = OrganizationLevel.objects.all()
        if len(all_org_levels) == 0:
            # No OrganizationLevels exist
            # That is a valid hierarchy
            return

        # Use generate_orglevel_hierarchy_list for basic validation
        # This will check that a single root orglevel, and each orglevel
        # in chain has at most a single child orglevel
        org_level_hier = cls.generate_orglevel_hierarchy_list(validate=True)
        if len(all_org_levels) != len(org_level_hier):
            # If valid, org_level_hier must contain all orglevels
            raise ValidationError('OrganizationLevel hierarchy issue: '
                'hierarchy size {} disagrees with total number {} of '
                'OrganizationLevels'.format(len(org_level_hier), 
                    len(all_org_levels)))

        # At this point, all orglevels in org_level_hier, so we have a
        # basic chain and no outliers.
        # Now just ensure levels are OK, names unique, and not too many
        # exporting to Xdmod
        allnames = set()
        lastlevel = None
        xdmod_exporters = set()
        lastorglev = None

        for orglev in org_level_hier:
            level = orglev.level
            if lastlevel is None:
                # We must be on root orglevel, no check needed
                pass
            else:
                # Ensure our level is less than parent
                if not lastlevel > level:
                    raise ValidationError('OrganizationLevel hierarchy issue: '
                            'parent OrgLevel {} with level={} is not greater '
                            'than child OrgLevel {} with level={}'.format(
                                lastorglev, lastlevel, orglev, level))
            lastorglev = orglev
            lastlevel = level

            name = orglev.name
            if name in allnames:
                raise ValidationError('OrganizationLevel hierarchy issue: '
                        'multiple OrganizationLevels with name {}'.format(
                            name))
            allnames.add(name)

            xdmod_exporters.add(orglev)

        # All checks passed
        return
    #end: def validate_orglevel_hierarchy

    @classmethod
    def add_organization_level(cls, name, level, parent, export_to_xdmod):
        """Adds a new organization level to the hierarchy.

        This adds a new org level with name, level, export_to_xdmod,  and 
        parent, repairing the hierarchy.  It will also add Organizations if
        needed to repair the Organization hierarchy.

        If the parent is None, then level must be greater than the level
        for any existing org level, and the new level will be the new root
        organization level.  The previous root org level will then but updated 
        to have the new org level as its parent.  If there are Organizations
        having the previous root as their OrgLevel, a new 'Unknown' root-level
        Organization will be created and all the Organizations previously at
        root-level will be made children of it.

        If a parent org level is given, and that parent does not have a
        child org level, than we simply add our new level beneath it.  The
        level given for the new org level must be less than that of the parent.
        For this case, this script is not really needed.

        If a parent org level is given and the parent has a child org level,
        then the given level must be between the parent and child levels,
        and the new org level will be added in between those two in the
        hierarchy.  For each Organization found at the child org level, we will
        create a placeholder Organization at the newly inserted OrgLevel
        and set the new Organization's parent to that of the Organization at
        the child OrgLevel, and sets that Organization's parent to the newly
        inserted Organization.

        For most cases this method will temporarily disable the validation
        checks (which would otherwise prevent the addition of the org level).

        Returns the newly created OrganizationLevel
        """
        if parent is None:
            # No parent organization
            root = cls.root_organization_level()
            if root:
                # A root allocation exists; we will replace as root
                if not level > root.level:
                    raise ValidationError( 'Attempt to install new root '
                        'orglevel {} with level {} is less than existing '
                        'root {} with level {}'.format(
                        name, level, root, root.level))
                # Replace root orglevel
                cls.disable_validation_checks(True)
                newroot = OrganizationLevel(
                        name=name, level=level, parent=None)
                newroot.save()
                root.parent = newroot
                root.save()
                cls.disable_validation_checks(False)

                # Delete any cached toplevel unknown org
                Organization.CACHED_TOPLEVEL_UNKNOWN_ORG = None
                # Are there any Organizations with OrgLevel=root ?
                orgs = Organization.objects.filter(organization_level=root)
                if orgs:
                    # Yes, so we need to create a placeholder root Organization
                    rootorg = Organization.get_or_create_unknown_root()
                    # And make that the parent to all previously root-level
                    # organizations
                    for org in orgs:
                        org.parent=rootorg
                        org.save()
                return newroot
            else:
                # No root allocation (so no hierarchy)
                # Just add the first entry
                newroot = OrganizationLevel(
                        name=name, level=level, parent=None)
                newroot.save()
                return newroot
        else:
            if not parent.level > level:
                raise ValidationError( 'Attempt to install new orglevel '
                    '{} with level {} is more than parent '
                    '{} with level {}'.format(
                    name, level, parent, parent.level))

            # We were given a parent, see if it has a child
            child = OrganizationLevel.objects.filter(parent=parent)
            if child:
                # Child queryset not empty, set child to first
                child = child[0]
                # Parent has a child, we go in between
                if not level > child.level:
                    raise ValidationError( 'Attempt to install new orglevel '
                        '{} with level {} is less than child '
                        '{} with level {}'.format(
                        name, level, child, child.level))
                cls.disable_validation_checks(True)
                newolev = OrganizationLevel(
                        name=name, level=level, parent=None)
                newolev.save()
                child.parent = newolev
                child.save()
                newolev.parent = parent
                newolev.save()
                cls.disable_validation_checks(False)

                # Are there any Organizations with OrgLevel=child ?
                orgs = Organization.objects.filter(organization_level=child)
                for org in orgs:
                    # For each Org at OrgLevel=child, we create a new 
                    # placeholder Org to sit between the child and parent Org
                    uniq_names = Organization.generate_unique_organization_names(
                        code='{}{}'.format('placeholder', org.code),
                        shortname='{}{}'.format('placeholder', org.shortname),
                        longname='{}{}'.format('placeholder', org.longname),
                        parent=org.parent)
                    neworg = Organization(code=uniq_names['code'],
                            shortname=uniq_names['shortname'],
                            longname=uniq_names['longname'],
                            organization_level=newolev,
                            parent=org.parent)
                    neworg.save()
                    org.parent = neworg
                    org.save()
                return newolev
            else:
                # Parent is childless, so simply add
                newolev = OrganizationLevel(
                        name=name, level=level, parent=parent)
                newolev.save()
                return newolev
    #end: def add_organization_level

    def delete_organization_level(self):
        """Delete the invocant organization level from the hierarchy.

        This deletes the invocant org level, repairing the hierarchy.
        Any Organizations at the invocant Organization level will
        be removed from the hierarchy (by invoking the method
        Organization._remove_from_hierarchy) and then deleted.
        Then if the invocant OrganizationLevel has a child, then
        child will be updated to use the invocant OrganizationLevel's
        parent (or None if no parent) as its parent.

        To work properly, we disable validation checks for both
        Organization and OrganizationLevel for parts of this method.
        """
        # See if there are any Organizations with invocant OrgLevel.
        orgs = Organization.objects.filter(organization_level=self)
        if orgs:
            Organization.disable_validation_checks(True)
            for org in orgs:
                org._remove_from_hierarchy()
                org.delete()

        # Do we have a parent?
        if self.parent is None:
            # No parent, so we are at root level. Do we have a child?
            child = OrganizationLevel.objects.filter(parent=self)
            if child:
                # Have child but no parent
                # Make child new root level
                child = child[0]
                self.disable_validation_checks(True)
                child.parent = None
                child.save()
                self.delete()
                self.disable_validation_checks(False)
            else: #if child
                # No parent or child.  So this is the only OrgLevel
                # Just delete it
                self.delete()
            #end: if child
        else: #if self.parent is None
            # We have a parent. Do we have a child?
            child = OrganizationLevel.objects.filter(parent=self)
            if child:
                # Have parent and child
                child = child[0]

                # Set the child's parent to parent
                self.disable_validation_checks(True)
                child.parent = self.parent
                self.delete()
                self.disable_validation_checks(False)
            else: #if child
                # Have a parent but no child
                # Just delete it
                self.delete()
            #end: if child
        #end: if self.parent is None

        # Enable ORganization validation checks
        Organization.disable_validation_checks(False)
        return
    #end: def delete_organization_level

#end: class OrganizationLevel

class Organization(TimeStampedModel):
    """This represents an organization, in a multitiered hierarchy.

    All organizational units, regardless of level are stored in this
    table.  Each links back to a specific OrganizationLevel, and can
    (and will unless at the highest organizational level) have a 
    parent which belongs to a higher organizational level.
    """
    
    parent = models.ForeignKey(
                'self', 
                on_delete=models.PROTECT,
                null=True, 
                blank=True,
            )
    organization_level = models.ForeignKey(
                OrganizationLevel, 
                on_delete=models.PROTECT,
                null=False,
            )
    code = models.CharField(
                max_length=512, 
                null=True, 
                blank=False, 
                unique=False,
                help_text='A short code for referencing this organization.  '
                    'Typically will be combined with short codes from all parents '
                    'to get an unique reference. May not contain hyphen (-)',
                validators=[
                    RegexValidator(
                        regex='-',
                        message='Code field may not contain hyphen (-)',
                        inverse_match=True,)
                    ],
            )
    shortname = models.CharField(
                max_length=1024, 
                null=True, 
                blank=False, 
                unique=False,
                help_text='A medium length name for this organization, used '
                    'in many displays.',
            )
    longname = models.CharField(
                max_length=2048, 
                null=True, 
                blank=False, 
                unique=False,
                help_text='The full name for this organization, for official '
                    'contexts',
            )
    is_selectable_for_user = models.BooleanField(
                default=True,
                help_text='This organization can be selected for Users',
            )
    is_selectable_for_project = models.BooleanField(
                default=True,
                help_text='This organization can be selected for Projects',
            )
    users = models.ManyToManyField(
                UserProfile, 
                through='OrganizationUser',
                related_name='organizations',
            )
    projects = models.ManyToManyField(
                Project,
                through='OrganizationProject',
                related_name='organizations',
            )
    # This is a cached top-level/root Unknown org, used for defaulting things
    CACHED_TOPLEVEL_UNKNOWN_ORG = None
    # Disable the validation constraints if true.
    # Intended for temporary use when adding/deleting OrgLevels (see
    # add_organization_level and delete_organization_level methods).
    _disable_validation_checks=False

    class Meta: #For Organization
        ordering = ['organization_level', 'code', ]
        constraints = [
                # Require code and parent be pairwise unique
                models.UniqueConstraint(
                    name='organization_code_parent_unique',
                    fields=[ 'code', 'parent' ]
                    ),
                # even when parent=NULL
                models.UniqueConstraint(
                    name='organization_code_nullparent_unique',
                    fields=['code'],
                    condition=Q(parent__isnull=True)
                    ),
                # Similar for shortname
                models.UniqueConstraint(
                    name='organization_shortname_parent_unique',
                    fields=[ 'shortname', 'parent' ]
                    ),
                models.UniqueConstraint(
                    name='organization_shortname_nullparent_unique',
                    fields=['shortname'],
                    condition=Q(parent__isnull=True)
                    ),
                # Similar for longname
                models.UniqueConstraint(
                    name='organization_longname_parent_unique',
                    fields=[ 'longname', 'parent' ]
                    ),
                models.UniqueConstraint(
                    name='organization_longname_nullparent_unique',
                    fields=['longname'],
                    condition=Q(parent__isnull=True)
                    ),
                ]
    #end: class Organization.Meta:

    def __str__(self):
        return self.shortname
    #end: def __str__

    @classmethod
    def disable_validation_checks(cls, new=None):
        """Accessor/mutator for _disable_validation_checks class data member.

        Because of the 'magic' done by django with class variables of Models,
        we must always use the explicit class name when referring to the
        class variable, otherwise we can end up with instance-like copies.

        To better support this, always use this accessor/mutator for getting or
        setting the value.
        """
        if new is not None:
            Organization._disable_validation_checks = new
        return Organization._disable_validation_checks
    #end: def disable_validation_checks

    def clean(self):
        """Validation: Ensure parent is of higher level than us.

        If we don't have a parent, then must be at highest organization
        level.
        If we do have a parent, it must be at a higher level and match
        the level of our org level parent.

        This is to prevent infinite recursion.
        """

        # Call base class's clean()
        super().clean()

        if self.disable_validation_checks():
            return

        # Get orglevel and orglevel's parent
        orglevel_obj = self.organization_level
        orglevel = orglevel_obj.level
        orglevel_parent = orglevel_obj.parent

        if orglevel_parent:
            # OrgLevel has a parent, so we are not at the highest level
            # So we must have a parent
            if not self.parent:
                raise ValidationError('Organization {}, level {} '
                        'is not top-level, but does not have parent'.format(
                            self, orglevel))
            # And it must have a higher org level than us
            parent_orglevel = self.parent.organization_level.level
            if parent_orglevel <= orglevel:
                raise ValidationError('Organization {}, level {} '
                        'has parent {} of lower level {}'.format(
                            self, orglevel, self.parent, parent_orglevel))
            # And it must match the level or orglevel_parent
            if parent_orglevel != orglevel_parent.level:
                raise ValidationError('Organization {}, level {} '
                        'has parent {} with level {} != '
                        'level {} of our orglevels parent'.format(
                            self, orglevel, self.parent, 
                            parent_orglevel, orglevel_parent.level))
        else:
            # OrgLevel does not have a parent, so neither should we
            if self.parent:
                raise ValidationError('Organization {}, level {} '
                        'is top-level, but has parent {}'.format(
                            self, orglevel, self.parent))

        return
    #end: def clean

    def save(self, *args, **kwargs):
        """Override save() to call full_clean first"""
        self.full_clean()
        return super(Organization, self).save(*args, **kwargs)
    #end: def save

    def _remove_from_hierarchy(self):
        """Remove invocant Organization from the hierarchy.

        This is a "private" method, not for "public" consumption.
        Basically a helper for OrganizationLevel.delete_organization_level

        This method removes the invocant from the Organization hierarchy
        in preparation for deleting it (typically for deleting the whole
        OrganizationLevel it is in).  It assumes that validation checks
        are already disabled, as some of what it does likely invalidates
        the checks.

        Basically, any child Organization of the invocant will have its
        parent set to the parent of the invocant.  Any Project or User
        associated with the invocant Organization will be disassociated 
        with the invocant and instead associated with the parent of the
        invocant. Specifically:

        For invocant Organization at the root OrganizationLevel (i.e.
        no parent Organization):
            * any children Organizations of the invocant will have their 
                parents set to None.  
            * any OrganizationUser or OrganizationProject instances that
                refer to the invocant Organization will be deleted.
        For invocant Organization at the leaf OrganizationLevel (i.e.
        has parent but no children):
            * any OrganizationUser or OrganizationProject instances that
                refer to the invocant Organization will be deleted and
                associated with the invocant's parent Organization (if
                it exists)
        For invocant Organization in a middle tier (i.e. has parent and
        children):
            * any child Organizations of the invocant will have their
                parents set to the parent of the invocant
            * any OrganizationUser or OrganizationProject instances that
                refer to the invocant will instead refer to the parent
        """
        parentOrg = self.parent

        # Set parents of children to our parent
        childOrgs = Organization.objects.filter(parent=self)
        for child in childOrgs:
            child.parent = parentOrg
            child.save()
        #end: for child in childOrgs

        # Handle projects refering to us
        orgprojs = OrganizationProject.objects.filter(organization=self)
        for orgproj in orgprojs:
            proj = orgproj.project
            is_primary = orgproj.is_primary
            # Delete the old
            orgproj.delete()
            # Update to the new
            if parentOrg:
                OrganizationProject.get_or_create_or_update_organization_project(
                        project=project, 
                        organization=parentOrg,
                        is_primary=is_primary,
                    )
            #end: if parentOrg
        #end: for orgproj in orgprojs

        # Handle Users refering to us
        orgusers = OrganizationUser.objects.filter(organization=self)
        for orguser in orgusers:
            user = orguser.user
            is_primary = orguser.is_primary
            # Delete the old
            orguser.delete()
            # Update to the new
            if parentOrg:
                OrganizationUser.get_or_create_or_update_organization_user(
                        user=user,
                        organization=parentOrg,
                        is_primary=is_primary,
                    )
            #end: if parentOrg
        #end: for orguser in orgusers
        return
    #end: def _remove_from_hierarchy

    @classmethod
    def validate_organization_hierarchy(
            cls,
            only_leaves_are_selectable_for_project=False,
            only_leaves_are_selectable_for_user=False,
            check_projects=True,
            check_users=True,
        ):
        """Perform various validation checks on Organization hierarchy.

        This performs various checks to ensure a valid hierarchy of
        Organizations, regardless of disable_validation_checks setting.

        We look at all Organizations, and verify that:
        1) If the Organization has a parent, then the OrgLevel of the 
        parent is the parent of the OrgLev of the original Organization
        2) If the Organization does not have a parent, then the ORgLevel
        of the Organization is the root OrgLevel
        3) If the only_leaves_are_selectable_for_user, then we require that
        any Org with is_selectable_for_user is at lowest/leaf error
        4) If the only_leaves_are_selectable_for_project, then we require that
        any Org with is_selectable_for_project is at lowest/leaf error
        5) If check_projects is True, we examine all projects and verify that:
        5a) every project has at most 1 organization marked as primary
        5b) every organization for the project is_selectable_for_project
        6) If check_users is True, we examine all users and verify that:
        6a) every user has at most 1 organization marked as primary
        6b) every organization for the user is_selectable_for_user

        If any issues found, raises a ValidationError exception.
        It will also produce a warning if disable_validation_checks is not
        set
        """
        if cls.disable_validation_checks():
            logger.warning('Organization disable_validation_checks is '
                'set')
            warnings.warn('Organization disable_validation_checks is '
                'set')

        # Get the OrganizationLevel hierarchy
        org_level_hier = OrganizationLevel.generate_orglevel_hierarchy_list()
        # and store root
        root_orglevel = org_level_hier[0]
        leaf_orglevel = org_level_hier[-1]
        parent_by_orglevel = {}
        lastolev = None
        for olev in org_level_hier:
            parent_by_orglevel[olev] = lastolev
            lastolev = olev

        # Get all Organizations
        all_orgs = Organization.objects.all()
        
        for org in all_orgs:
            olev = org.organization_level
            parent = org.parent
            olev_parent = parent_by_orglevel[olev]
            fcode = org.fullcode()

            if parent is None:
                # Require olev be root orglevel
                if olev != root_orglevel:
                    raise ValidationError('Organization {} has no parent, '
                            'but is not at OrgLevel {} != root OrgLevel {}'.format(
                                fcode, olev.name, root_orglevel.name))
                #end: if olev != root_orglevel
            else: #if parent is None
                #org level of parent must be olev_parent
                if olev_parent is None:
                    raise ValidationError('Organization {} is at OrgLevel {} '
                            'which has no parent, but Org has parent {}'.format(
                                fcode, olev.name, parent.fullcode()))
                else: #if olev_parent is None
                    parent_olev = parent.organization_level
                    if olev_parent != parent_olev:
                        raise ValidationError('Organization {} at OrgLevel {} '
                                'has parent Org {} at OrgLevel {}, but parent of '
                                '{} is {}'.format(
                                    fcode, olev.name,
                                    parent.fullcode(), parent.organization_level.name,
                                    olev.name, olev_parent.name))
                #end: if olev_parent is None
            #end: if parent is None

            if only_leaves_are_selectable_for_project:
                if org.is_selectable_for_project:
                    if olev != leaf_orglevel:
                        raise ValidationError('Organization {} is_selectable_for_project '
                                'but is at OrgLevel {} > leaf OrgLevel {}'.format(
                                    fcode, olev.name, leaf_orglevel.name))
                    #end: if olev != leaf_org_level
                #end: if org.is_selectable_for_project
            #end: if only_leaves_are_selectable_for_project

            if only_leaves_are_selectable_for_user:
                if org.is_selectable_for_user:
                    if olev != leaf_orglevel:
                        raise ValidationError('Organization {} is_selectable_for_user '
                                'but is at OrgLevel {} > leaf OrgLevel {}'.format(
                                    fcode, olev.name, leaf_orglevel.name))
                    #end: if olev != leaf_org_level
                #end: if org.is_selectable_for_user
            #end: if only_leaves_are_selectable_for_user

        #end: for org in all_orgs:

        if check_projects:
            # Verify all orgs for projects are selectable, and at most one is primary
            last = None
            # We want query to be ordered so all projects are together
            qset = OrganizationProject.objects.all().order_by('project__pk')
            for orgp in qset:
                if last is None or last['pk'] != orgp.project.pk:
                    last = {
                            'pk': orgp.project.pk,
                            'primary': None,
                        }
                if orgp.is_primary:
                    if last['primary'] is not None:
                        raise ValidationError('Project {} has multiple '
                                'organizations({} and {}) with is_primary set'.format(
                                    orgp.project.title,
                                    last['primary'].fullcode(), 
                                    orgp.organization.fullcode(),
                                ))
                    #end: if last['primary'] is not None
                    if not orgp.organization.is_selectable_for_project:
                        raise ValidationError('Project {} has Organization {} '
                            'which is not selectable_for_project'.format(
                                orgp.project.title,
                                orgp.organization.fullcode()
                            ))
        #end: if check_projects:
        if check_users:
            # Verify all orgs for users are selectable, and at most one is primary
            last = None
            # We want query to be ordered so all users are together
            qset = OrganizationUser.objects.all().order_by('user__user__pk')
            for orgu in qset:
                if last is None or last['pk'] != orgu.user.user.pk:
                    last = {
                            'pk': orgu.user.user.pk,
                            'primary': None,
                        }
                if orgu.is_primary:
                    if last['primary'] is not None:
                        raise ValidationError('Project {} has multiple '
                                'organizations({} and {}) with is_primary set'.format(
                                    orgu.user.user.username,
                                    last['primary'].fullcode(), 
                                    orgu.organization.fullcode(),
                                ))
                    #end: if last['primary'] is not None
                    if not orgu.organization.is_selectable_for_user:
                        raise ValidationError('Project {} has Organization {} '
                            'which is not selectable_for_user'.format(
                                orgu.user.user,username,
                                orgu.organization.fullcode()
                            ))
        #end: if check_users:
        return
    #end: def validate_organization_hierarchy(

    @classmethod
    def create_or_update_organization_by_parent_code(
                cls, 
                code, 
                organization_level, 
                shortname,
                longname,
                parent=None,
                is_selectable_for_user=True,
                is_selectable_for_project=True,
            ):
        """Create or update an Organization with given code/parent
        
        We check if an Organization exists with specified code and parent.
        If not, we create a new Organization with the fields as specified.
        If such an Organization exists, then we update the fields as 
        specified as need.

        organization_level can either be an OrganizationLevel instance
        or the name for such.
        parent can be None for no parent, or an OrganizationLevel, or
        the fullcode of an OrganizationLevel

        Returns a triplet (obj, created, changes)
        where
            obj is the new or previously-existing OrganizationLevel
            created is a boolean which is true if a new OrgLevel was created
            changes is a (possibly empty) indicating keyed on fields which
                were updated (if existing object updated), the value is 
                a dictionary with keys 'old' and 'new' giving the old and new
                values.
        """
        created = False
        changes = {}

        # Convert parent to an Organization instance
        if parent is None:
            # None is OK
            pass
        elif isinstance(parent, Organization):
            # Already an Organization, nothing to do
            pass
        elif isinstance(parent, str):
            # Got a string, convert to Organization
            pcode = parent
            parent = Organization.get_organization_by_fullcode(pcode)
        else:
            # Error
            raise ValueError('parent must be None, an Organization '
                    'instance, or the fullcode of an Organization')
        #end: if parent is None

        # Convert organization_level to an OrganizationLevel instance
        if organization_level is None:
            # None is OK
            pass
        elif isinstance(organization_level, OrganizationLevel):
            # Already an OrganizationLevel, nothing to do
            pass
        elif isinstance(organization_level, str):
            # Got a string, convert to OrganizationLevel
            olname = organization_level
            organization_level = OrganizationLevel.objects.get(name=olname)
        else:
            # Error
            raise ValueError('organization_level must be None, an OrganizationLevel '
                    'instance, or the name of an OrganizationLevel')
        #end: if organization_level is None

        # See if Organization exists
        qset = Organization.objects.filter(parent=parent, code=code)
        if qset:
            # Organization with specified parent and code exists, update
            # fields as needed
            obj = qset[0]

            # OrganizationLevel
            needs2change=False
            old = obj.organization_level
            if old is None:
                if organization_level is not None:
                    needs2change = True
            else:
                if organization_level is None or organization_level != old:
                    needs2change = True
            #end: if old is None
            if needs2change:
                obj.organization_level = organization_level
                obj.save()
                changes['organization_level'] = { 'old':old, 'new':organization_level }

            # Shortname
            needs2change=False
            old = obj.shortname
            if old is None:
                if shortname is not None:
                    needs2change = True
            else:
                if shortname is None or shortname != old:
                    needs2change = True
            #end: if old is None
            if needs2change:
                obj.shortname = shortname
                obj.save()
                changes['shortname'] = { 'old':old, 'new':shortname }

            # Longname
            needs2change=False
            old = obj.longname
            if old is None:
                if longname is not None:
                    needs2change = True
            else:
                if longname is None or longname != old:
                    needs2change = True
            #end: if old is None
            if needs2change:
                obj.longname = longname
                obj.save()
                changes['longname'] = { 'old':old, 'new':longname }

            # Is_selectable_for_user
            needs2change=False
            old = obj.is_selectable_for_user
            if old is None:
                if is_selectable_for_user is not None:
                    needs2change = True
            else:
                if is_selectable_for_user is None or is_selectable_for_user != old:
                    needs2change = True
            #end: if old is None
            if needs2change:
                obj.is_selectable_for_user = is_selectable_for_user
                obj.save()
                changes['is_selectable_for_user'] = { 'old':old, 'new':is_selectable_for_user }

            # Is_selectable_for_project
            needs2change=False
            old = obj.is_selectable_for_project
            if old is None:
                if is_selectable_for_project is not None:
                    needs2change = True
            else:
                if is_selectable_for_project is None or is_selectable_for_project != old:
                    needs2change = True
            #end: if old is None
            if needs2change:
                obj.is_selectable_for_project = is_selectable_for_project
                obj.save()
                changes['is_selectable_for_project'] = { 'old':old, 'new':is_selectable_for_project }

        else: #if qset
            # Need to create a new Organization
            created = True
            obj = Organization.objects.create(
                    code=code,
                    parent=parent,
                    organization_level=organization_level,
                    shortname=shortname,
                    longname=longname,
                    is_selectable_for_user=is_selectable_for_user,
                    is_selectable_for_project=is_selectable_for_project,
                )
            changes = {
                    'code': { 'old':None, 'new':code },
                    'parent': { 'old':None, 'new':parent },
                    'organization_level': { 'old':None, 'new':organization_level },
                    'shortname': { 'old':None, 'new':shortname },
                    'longname': { 'old':None, 'new':longname },
                    'is_selectable_for_user': { 'old':None, 'new':is_selectable_for_user },
                    'is_selectable_for_project': { 'old':None, 'new':is_selectable_for_project },
                }
        #end: if qset
        return obj, created, changes
    #end: def create_or_update_organization_by_parent_code

    def ancestors(self):
        """Returns of list ref of all ancestors.

        Returns a list like [grandparent, parent]
        Returns empty list if no parent, otherwise returns the
        parent's ancestors() with parent appended.
        """
        retval = []
        if self.parent:
            retval = self.parent.ancestors()
            retval.append(self.parent)
        return retval
    #end: def ancestors
                
    def descendents(self):
        """Returns of list ref of all descendents

        Returns a list like [ child1, child2, ... grandchild1, ... ]
        Returns empty list if no children, otherwise returns a list
        with all of invocant's children, and all of there children, etc.
        """
        # Get immediate children
        import sys
        children = list(Organization.objects.filter(parent=self))
        retval = children
        for child in children:
            # For each child, get it's descendents
            tmp = child.descendents()
            retval.extend(tmp)
        # Deduplicate
        retval = list(set(retval))
        return retval
    #end: def descendents
                
    def fullcode(self):
        """Returns a full code, {parent_code}-{our_code}."""
        retval = self.code
        if self.parent:
            retval = '{pcode}-{code}'.format(
                    pcode=self.parent.fullcode(),
                    code=retval)
        return retval
    #end: def fullcode

    def semifullcode(self):
        """Returns full code of our parent, hyphen, our short name."""
        retval = self.shortname
        if self.parent:
            retval = '{pcode}-{code}'.format(
                    pcode=self.parent.fullcode(),
                    code=retval)
        return retval
    #end: def semifullcode

    def __str__(self):
        return self.fullcode()
    #end: def __str__

    def next_xdmod_exported_organization(self):
        """Returns the next Org whose OrgLevel is exported to xdmod.

        This method returns the next Organization whose OrganizationLevel
        has export_to_xdmod set, starting with the invocant.

        If the OrganizationLevel of the invocant has export_to_xdmod set,
        returns it.  Otherwise, goes through the ancestors of the invocant,
        and returns the first one with export_to_xdmod set.  Returns None
        if no ancestor with export_to_xdmod found.
        """
        orglevel = self.organization_level
        if orglevel.export_to_xdmod:
            return self

        # Invocant is not of an exported OrgLevel
        # We reverse to get parent, grandparent, great-grandparent, ... order
        ancestors = self.ancestors()
        ancestors.reverse()
        for anc in ancestors:
            if anc.organization_level.export_to_xdmod:
                return anc

        # Nothing matched
        return None
    #end: def next_xdmod_exported_organization

    @classmethod
    def get_organization_by_fullcode(cls, fullcode):
        """Class method which returns organization with given fullcode.

        This will get the Organization with the given full code. If such
        an Organization object is found, returns it.  Returns None if not
        found.
        """
        codes = fullcode.split('-')
        lastcode = codes[-1]
        orgs = cls.objects.filter(code__exact=lastcode)
        if len(codes) > 1:
            for org in orgs:
                if org.fullcode() == fullcode:
                    return org
            return None
        else:
            if len(list(orgs)) > 0:
                # Should we validate that is unique?  
                # DB constraints say should be
                return list(orgs)[0]
            else:
                return None
    #end: def get_organization_by_fullcode

    @classmethod
    def get_organization_by_semifullcode(cls, fullcode):
        """Class method which returns organization with given fullcode.

        This will get the Organization with the given full code. If such
        an Organization object is found, returns it.  Returns None if not
        found.
        """
        codes = fullcode.split('-')
        lastcode = codes[-1]
        orgs = cls.objects.filter(shortname__exact=lastcode)
        if len(codes) > 1:
            for org in orgs:
                if org.semifullcode() == fullcode:
                    return org
            return None
        else:
            if len(list(orgs)) > 0:
                # Should we validate that is unique?  
                # DB constraints say should be
                return list(orgs)[0]
            else:
                return None
    #end: get_organization_by_semifullcode

    @classmethod
    def generate_unique_organization_names(cls, 
            code='Unknown', 
            shortname='Unknown', 
            longname='Unknown', 
            parent=None):
        """This find unique code/shortname/longname for a new Organization.

        Parent can be None for a root level Organization, or reference an
        existing Organization.  We will find a set of code, shortname, and
        longname which begins with the values specified, but does not occur
        among the current children of the parent.  These are returned as
        a dictionary with keys 'code', 'shortname', and 'longname', resp.
        """
        all_children = None
        if parent is None:
            all_children = cls.objects.filter(parent__isnull=True)
        else:
            all_children = cls.objects.filter(parent=parent)

        all_codes = set()
        all_snames = set()
        all_lnames = set()
        for child in all_children:
            all_codes.add(child.code)
            all_snames.add(child.shortname)
            all_lnames.add(child.longname)

        # Find unique values
        retval = {}

        # Get unique code
        if code in all_codes:
            i = 1
            test = '{}{}'.format(code,i)
            while test in all_codes:
                i = i+1
                test = '{}{}'.format(code,i)
            code = test
        retval['code'] = code

        # Get unique shortname
        if shortname in all_snames:
            i = 1
            test = '{}{}'.format(shortname,i)
            while test in all_snames:
                i = i+1
                test = '{}{}'.format(shortname,i)
            shortname = test
        retval['shortname'] = shortname

        # Get unique longname
        if longname in all_lnames:
            i = 1
            test = '{}{}'.format(longname,i)
            while test in all_lnames:
                i = i+1
                test = '{}{}'.format(longname,i)
            longname = test
        retval['longname'] = longname

        return retval
    #end: deef generate_unique_organization_names

    @classmethod
    def get_or_create_unknown_root(cls, dryrun=False):
        """This returns a 'top-level' Unknown organization.

        It will look for one, first checking if it is cached
        in CACHED_TOPLEVEL_UNKNOWN_ORG, then searching DB, 
        and return if found.  

        If not found, creates one.  The value being returned will
        be cached in UNKNOWN_ORG to speed up future calls.

        If dryrun is set, will not actually create an instance but
        just return None
        """
        if cls.CACHED_TOPLEVEL_UNKNOWN_ORG is not None:
            # We have a cached value, use it
            return cls.CACHED_TOPLEVEL_UNKNOWN_ORG

        # No value cached in UNKNOWN_ORG, look for one in DB
        # To allow this to work when adding a new root orglevel, we
        # need to search for orglevel having no parent, not for org
        # to have no parent (between creation of new root and migrating
        # old root level orgs to new root org, the orgs at old root will
        # have no parent and be picked up)
        qset = cls.objects.filter(
                code='Unknown', 
                #parent__isnull=True,
                organization_level__parent__isnull=True,
                )
        if qset:
            # We got an org with code='Unknown', cache and return first found
            cls.CACHED_TOPLEVEL_UNKNOWN_ORG = qset[0]
            return qset[0]

        if dryrun:
            return None
        #Not found, create one
        orglevel = OrganizationLevel.root_organization_level()
        if not orglevel:
            raise OrganizationLevel.DoesNotExist('No parentless OrganizationLevel found')
        unique_names = cls.generate_unique_organization_names(
                parent=None,
                code='Unknown',
                shortname='Unknown',
                longname='Container for Unknown organizations'
                )

        new = cls.objects.create(
                code=unique_names['code'],
                parent=None,
                organization_level=orglevel,
                shortname=unique_names['shortname'],
                longname=unique_names['longname'],
                is_selectable_for_user=False,
                is_selectable_for_project=False,
                )
        # Cache it
        cls.CACHED_TOPLEVEL_UNKNOWN_ORG = new
        return new
    #end: def get_or_create_unknown_root

    @classmethod
    def create_unknown_object_for_dir_string(cls, dirstring, dryrun=False):
        """This creates a placeholder Organization for the 
        given Directory string.

        A new Organization will be created under the top-
        level Unknown Organization, and will create a
        Directory2Organization object refering to it.
        The new Organization will be named Unknown_dddd
        where dddd is some number.

        This is to help facilitate admins fixing things
        afterwards --- either by merging the new directory
        string with an existing Organization or creating 
        a new one.

        The newly created Organization is returned.
        """
        unknown_root = cls.get_or_create_unknown_root(dryrun)
        orglevel = None
        if unknown_root is not None:
            root_orglevel = unknown_root.organization_level
            orglevel = root_orglevel.child_organization_level()
        unique_names = cls.generate_unique_organization_names(
                parent=unknown_root,
                code='Unknown_placeholder',
                shortname='Unknown: {}'.format(dirstring),
                longname='Unknown: {}'.format(dirstring)
                )
        placeholder = cls(
            code=unique_names['code'],
            parent=unknown_root,
            organization_level=orglevel,
            shortname=unique_names['shortname'],
            longname=unique_names['longname']
            )
        if not dryrun:
            placeholder.save()
        tmpid = placeholder.id
        if tmpid is None:
            tmpid = abs(hash(dirstring))
            placeholder.id = tmpid
        placeholder.code = 'Unknown_{}'.format(tmpid)
        if not dryrun:
            placeholder.save()
            Directory2Organization.objects.create(
                    organization=placeholder,
                    directory_string=dirstring).save()
        return placeholder
    #end: def create_unknown/object_for_dir_string

#end: class Organization

class OrganizationProject(TimeStampedModel):
    """This table associates Organizations with Projects.

    There is an additional field 'is_primary' which marks an Organization
    as the "primary" Organization for the Project.  At most one Organization
    per Project can be marked as such.  

    Many processes only look at "primary" Organizations of a project, but
    one can associate as many "secondary" Organizations with a project as
    desired.
    """
    organization = models.ForeignKey(
            Organization,
            on_delete=models.CASCADE, 
            null=False,
            blank=False,
        )
    project = models.ForeignKey(
            Project,
            on_delete=models.CASCADE, 
            null=False,
            blank=False,
        )
    is_primary = models.BooleanField(
            default=False,
            help_text="Mark as Project's 'primary' Organization.  A "
                "Project can have at most one primary Organization",
        )
    class Meta: #For OrganizationProject
        # Force a deterministic ordering
        # Entries with is_primary==True always come first
        # Next ordered by Organization (code, then pk), then
        # ordered by Project (title, then pk)
        ordering = ['-is_primary', 
                'organization__code', 'organization__pk', 
                'project__title', 'project__pk'
            ]
        constraints = [
                # Require organization and project be pairwise unique
                models.UniqueConstraint(
                    name='organizationproject__organization_project_unique',
                    fields=[ 'organization', 'project' ]
                    ),
                # Require project to be unique if is_primary is True
                # This means a Project can have at most one "primary" Organization
                models.UniqueConstraint(
                    name='organizationproject_project_unique_when_is_primary',
                    fields=['project'],
                    condition=Q(is_primary=True)
                    ),
                ]
    #end: class OrganizationProject.Meta

    @classmethod
    def get_primary_organization_for_project(cls, project):
        """Returns the 'primary' Organization for specified Project.

        Returns None if no primary Organization.
        """
        qset = cls.objects.filter(project=project, is_primary=True)
        if qset:
            obj = qset[0]
            primary_org = obj.organization
        else:
            primary_org = None
        return primary_org
    #end: def get_primary_organization_for_project

    @classmethod
    def set_primary_organization_for_project(cls, project, new):
        """Sets the 'primary' Organization for specified Project.

        If the Project already has a 'primary' Organization, it
        is demoted to secondary.  If there is already a OrganizationProject
        with project=project and organization=new, the is_primary
        flag is set; otherwise a new OrganizationProject is created.

        The return value is the old 'primary' Organization for the
        Project, or None if there was none, and the OrganizationProject
        instance
        """
        oldprimary_org = None
        # Does project already have a primary Organization
        qset = cls.objects.filter(project=project, is_primary=True)
        if qset:
            # Yes, demote it
            oldobj = qset[0]
            oldprimary_org = oldobj.organization
            oldobj.is_primary = False
            oldobj.save()
        else:
            oldprimary_org = None

        # Is new already an Organization of Project
        qset = cls.objects.filter(project=project, organization=new)
        if qset:
            # Yes, promote it
            obj = qset[0]
            obj.is_primary = True
            obj.save()
        else:
            # No, add it
            obj = cls.objects.create(
                    project=project, 
                    organization=new,
                    is_primary=True,
                )
        return oldprimary_org, obj
    #end: def set_primary_organization_for_project

    @classmethod
    def get_or_create_or_update_organization_project(
            cls, organization, project, is_primary=False):
        """Like get_or_create, but will update if existing and is_primary changed.

        Checks if an OrganizationProject with specified organization and
        project exists.  If yes, then updates is_primary field to what was
        specified if needed.  If not, then creates with is_primary as
        specified.

        Returns tuplet (obj, created, changes) where:
            obj is the OrganizationProject found/created/updated
            created is boolean, true if obj was newly created
            changes is dictionary.  Keys are the names of fields that
                were changed, and value is a dictionary with keys
                'old' and 'new' giving old and new values for the
                field.
        For a newly created instance, all three fields will be present
        in changes, with 'old' set to None and 'new' set to the values given
        For an existing instance, if is_primary was updated, it will be
        the only element of dictionary; otherwise will be an empty 
        dictionary.
        If is_primary is true, changes will also have an entry with
        the key 'primary_organization', and the subkey old will have
        the Organization which previously was primary for this Project
        as a value, and new for new.

        """
        created = False
        changes = {}
        qset = cls.objects.filter(
                organization=organization, project=project)

        if qset:
            # Existing OrganizationProject found
            obj = qset[0]
            old = obj.is_primary
            need2change = False
            if old is None:
                if is_primary is not None:
                    need2change = True
            else:
                if is_primary is None or is_primary != old:
                    need2change = True
            if need2change:
                if is_primary:
                    # If is_primary is set, we need to handle with care
                    # to avoid two primary organizations.
                    oldprimary = cls.set_primary_organization_for_project(
                           project=project, new=organization)
                    changes['primary_organization'] = {
                            'old':oldprimary, 'new':organization }
                else:
                    # If not is_primary, can just update field
                    obj.is_primary = is_primary
                    obj.save()
                changes['is_primary'] = { 'old':old, 'new':is_primary }
        else: #if qset
            # No previously existing object, create a new one
            created = True
            if is_primary:
                # Again, special handling
                oldprimary, obj = cls.set_primary_organization_for_project(
                       project=project, new=organization)
                changes['primary_organization'] = {
                        'old':oldprimary, 'new':organization }
            else:
                # Not is_primary, can just create
                obj = cls.objects.create(
                        project=project, 
                        organization=organization,
                        is_primary=is_primary)
            changes['project'] = project,
            changes['organization'] = organization,
            changes['is_primary'] = is_primary
        return obj, created, changes
    #end: def get_or_create_or_update_organization_project

    @classmethod
    def set_organizations_for_project(
            cls, project, organization_list, 
            delete=False, default_first_primary=False):
        """Updates the organizations associated with project from list

        Given an Project and a list of Organizations, update 
        the Organizations associated with the Project.

        The elements of organization_list can be:
            a dict with keys 'organization' and 'is_primary'
                The value for the organization key can be an instance
                of Organization or the fullcode of an Organization
            an Organization instance
            the fullcode of an Organization.
        If the Organization was provided as instance or fullcode, or
        as a dictionary w/out the 'is_primary' key, is_primary will
        default to False *unless* default_first_primary is set AND
        it is the first element of the list.

        If is_primary is set, any previously primary Organization for
        the Project (including if it was previously set by an earlier
        entry in this object list) is demoted to secondary and the
        current Organization is made primary.

        If delete is False (the default), the Organizations in
        organization_list are added to the set of Organizations for
        the Project, and any previously existing Organizations for the
        project are left alone (with the exception that a primary Organization
        might be demoted to secondary if we added a new primary).
        If delete is True, any previously existing Organizations for the
        Project not included in the organization_list will be disassociated
        with the Project; i.e. the resulting set of Organizations will match
        organization_list.

        Returns a dictionary indicating changes made; keys are of the
        form 'Org[fcode]' where fcode is the fullcode of the Organization
        that was updated, and value is a dictionary with keys 'old' and 'new'.
        The old and new keys can have the following values:
            None: not present.  I.e., if in old it means the org was newly
                associated with the project, in new it means was disassociated.
            'primary': there is/was an entry with 'is_primary' flag true
            'secondary': there is/was an entry with 'is_primary' False
        """
        changes = {}
        keypattern = 'Org[{}]'
        if delete:
            # Delete flag set, we need the list of previously existing
            # Organizations
            qset = cls.objects.filter(project=project)
            previous_by_fullcode = {}
            fcodes2del = set()
            if qset:
                for rec in qset:
                    org = rec.organization
                    fcode = org.fullcode()
                    previous_by_fullcode[fcode] = rec
                    fcodes2del.add(fcode)

        first = default_first_primary
        for orec in organization_list:
            # Default is_primary to False, unless first iteration and default_first_primary
            is_primary = first
            first = False
            # Handle is orec is a dict
            if isinstance(orec, dict):
                # We got a dictionary
                tmporec = orec
                if 'organization' in tmporec:
                    orec = tmporec['organization']
                else:
                    raise ValueError('Dictionary elements of organization_list '
                            '*must* have an "organization" key')
                    if 'is_primary' in tmporec:
                        is_primary = tmporec['is_primary']
            # Get Organization from orec
            if isinstance(orec, Organization):
                # Already an Organization
                org = orec
            elif isinstance(orec, str):
                # Should be fullcode of an Organization
                org = Organization.get_organization_by_fullcode(orec)
            else:
                raise ValueError('Elements of organization_list must either be '
                        'an instance of Organization, a string with fullcode of '
                        'an Organization, or a dict with organization key with '
                        'instance or fullcode as value')

            # Add the Organization
            fcode = org.fullcode()
            key = keypattern.format(fcode)
            if fcode in previous_by_fullcode:
                # Organization already present for Project, update is_primary as needed
                old = previous_by_fullcode[fcode]
                if old.is_primary != is_primary:
                    if is_primary:
                        # Handle primary orgs delicately
                        oldprimary, _ = cls.set_primary_organization_for_project(
                                project=project, new=org)
                        opkey = None
                        if oldprimary:
                            opkey = keypattern.format(oldprimary.fullcode())
                        if opkey in changes:
                            changes[opkey][new] = 'secondary'
                        else:
                            changes[opkey]={'old':'primary', 'new':'secondary'}
                        if key in changes:
                            changes[key][new] = 'primary'
                        else:
                            changes[key] = { 'old':None, 'new':'primary' }
                    else: #if is_primary
                        old.is_primary = False
                        old.save()
                        if key in changes:
                            changes[key][new] = 'secondary'
                        else:
                            changes[key] = { 'old':primary, 'new':'secondary' }
                    #end: if is_primary
                #end: if old.is_primary != is_primary
            else: #if fcode in previous_by_fullcode
                # Need to add
                if is_primary:
                    # Special care for primary orgs
                    oldprimary, _ = cls.set_primary_organization_for_project(
                            project=project, new=org)
                    opkey = None
                    if oldprimary:
                        opkey = keypattern.format(oldprimary.fullcode())
                    if opkey in changes:
                        changes[opkey][new] = 'secondary'
                    else:
                        changes[opkey]={'old':'primary', 'new':'secondary'}
                    if key in changes:
                        changes[key][new] = 'primary'
                    else:
                        changes[key] = { 'old':None, 'new':'primary' }
                else: #if is_primary:
                    cls.objects.create(
                            organization=org, project=project, is_primary=False)
                    if key in changes:
                        changes[key][new] = 'secondary'
                    else:
                        changes[key] = { 'old':None, 'new':'secondary' }
                #end: if is_primary:
            #end: if fcode in previous_by_fullcode

            # Remove our fullcode from list of those previously present
            fcodes2del.discard(fcode)
        #end: for orec

        if delete:
            # delete Organizations not on our list
            for fcode in fcodes2del:
                key = keypattern.format(fcode)
                orgp = previous_by_fullcode[fcode]
                isprimary = orgp.is_primary
                orgp.delete()
                if key in changes:
                    changes[key][new] = None
                else:
                    old = 'secondary'
                    if isprimary:
                        old = 'primary'
                    changes[key] = { 'old':old, 'new':None }
            #end: for fcode
        #end: if delete

        # Remove redundant keys
        for key in changes:
            old = changes[key]['old']
            new = changes[key]['new']
            if old is None and new is None:
                del changes[key]
            elif old is not None and new is not None and old == new:
                del changes[key]
        #end: for key in changes

        return changes
    #end: def set_organizations_for_project

    @classmethod
    def delete_organizations_for_project(
            cls, project, organization_list, 
            ):
        """Deletes the organizations associated with project from list

        Given an Project and a list of Organizations, disassociate the
        Organizations in the list from the Project.

        The elements of organization_list can be:
            a dict with keys 'organization' ('is_primary' can also
                be given, but is not used by this method)
                The value for the organization key can be an instance
                of Organization or the fullcode of an Organization
            an Organization instance
            the fullcode of an Organization.
        
        Returns a dictionary summarizing changes.  Key will be of the
        for Org[fcode], value will be a subdictionary with keys 'old' and
        'new':  'new' should always be None, 'old' can be 'primary' or
        'secondary' according to whether the orignal entry had 'is_primary'
        set or not
        """
        changes = {}
        keypattern = 'Org[{}]'
        for orec in organization_list:
            # Handle is orec is a dict
            if isinstance(orec, dict):
                # We got a dictionary
                tmporec = orec
                if 'organization' in tmporec:
                    orec = tmporec['organization']
                else:
                    raise ValueError('Dictionary elements of organization_list '
                            '*must* have an "organization" key')
            # Get Organization from orec
            if isinstance(orec, Organization):
                # Already an Organization
                org = orec
            elif isinstance(orec, str):
                # Should be fullcode of an Organization
                org = Organization.get_organization_by_fullcode(orec)
            else:
                raise ValueError('Elements of organization_list must either be '
                        'an instance of Organization, a string with fullcode of '
                        'an Organization, or a dict with organization key with '
                        'instance or fullcode as value')

                # Delete the Organization from Project
                qset = cls.objects.filter(project=project, organization=org)
                if qset:
                    # Got a match
                    orgp = qset[0]
                    key = keypattern.format(orgp.fullcode())
                    old = 'secondary'
                    if orgp.is_primary:
                        old = 'primary'
                    orgp.delete()
                    changes[key] = { 'old':old, 'new':None }
        #end for orec in organization_list:
        return changes
    #end: def delete_organizations_for_project

#end: class OrganizationProject

class OrganizationUser(TimeStampedModel):
    """This table associates Organizations with Users.

    There is an additional field 'is_primary' which marks an Organization
    as the "primary" Organization for the User.  At most one Organization
    per User can be marked as such.  

    Many processes only look at "primary" Organizations of a user, but
    one can associate as many "secondary" Organizations with a user as
    desired.
    """
    organization = models.ForeignKey(
            Organization,
            on_delete=models.CASCADE, 
            null=False,
            blank=False,
        )
    user = models.ForeignKey(
            UserProfile,
            on_delete=models.CASCADE, 
            null=False,
            blank=False,
        )
    is_primary = models.BooleanField(
            default=False,
            help_text="Mark as User's 'primary' Organization.  A "
                "User can have at most one primary Organization",
        )
    class Meta: #For OrganizationUser
        # Force a deterministic ordering
        # Entries with is_primary==True always come first
        # Next ordered by Organization (code, then pk), then
        # ordered by User (username, then pk)
        ordering = ['-is_primary', 
                'organization__code', 'organization__pk', 
                'user__user__username', 'user__user__pk'
            ]
        constraints = [
                # Require organization and user be pairwise unique
                models.UniqueConstraint(
                    name='organizationuser__organization_user_unique',
                    fields=[ 'organization', 'user' ]
                    ),
                # Require user to be unique if is_primary is True
                # This means a User can have at most one "primary" Organization
                models.UniqueConstraint(
                    name='organizationuser_user_unique_when_is_primary',
                    fields=['user'],
                    condition=Q(is_primary=True)
                    ),
                ]
    #end: class OrganizationUser.Meta

    @classmethod
    def get_primary_organization_for_user(cls, user):
        """Returns the 'primary' Organization for specified User.

        Returns None if no primary Organization.
        """
        qset = cls.objects.filter(user=user, is_primary=True)
        if qset:
            obj = qset[0]
            primary_org = obj.organization
        else:
            primary_org = None
        return primary_org
    #end: def get_primary_organization_for_user

    @classmethod
    def set_primary_organization_for_user(cls, user, new):
        """Sets the 'primary' Organization for specified User.

        user can be either an instance of User or UserProfile

        If the User already has a 'primary' Organization, it
        is demoted to secondary.  If there is already a OrganizationUser
        with user=user and organization=new, the is_primary
        flag is set; otherwise a new OrganizationUser is created.

        The return value is the old 'primary' Organization for the
        User, or None if there was none, and the OrganizationUser
        instance
        """
        oldprimary_org = None
        # Convert user to UserProfile
        if isinstance(user, UserProfile):
            # Already is, nothing to do
            pass
        elif isinstance(user, User):
            user = user.userprofile
        else:
            raise ValueError('user must be instance of User or UserProfile')

        # Does user already have a primary Organization
        qset = cls.objects.filter(user=user, is_primary=True)
        if qset:
            # Yes, demote it
            oldobj = qset[0]
            oldprimary_org = oldobj.organization
            oldobj.is_primary = False
            oldobj.save()
        else:
            oldprimary_org = None

        # Is new already an Organization of User
        qset = cls.objects.filter(user=user, organization=new)
        if qset:
            # Yes, promote it
            obj = qset[0]
            obj.is_primary = True
            obj.save()
        else:
            # No, add it
            obj = cls.objects.create(
                    user=user, 
                    organization=new,
                    is_primary=True,
                )
        return oldprimary_org, obj
    #end: def set_primary_organization_for_user

    @classmethod
    def get_or_create_or_update_organization_user(
            cls, organization, user, is_primary=False):
        """Like get_or_create, but will update if existing and is_primary changed.

        Checks if an OrganizationUser with specified organization and
        user exists.  If yes, then updates is_primary field to what was
        specified if needed.  If not, then creates with is_primary as
        specified.

        Returns tuplet (obj, created, changes) where:
            obj is the OrganizationUser found/created/updated
            created is boolean, true if obj was newly created
            changes is dictionary.  Keys are the names of fields that
                were changed, and value is a dictionary with keys
                'old' and 'new' giving old and new values for the
                field.
        For a newly created instance, all three fields will be present
        in changes, with 'old' set to None and 'new' set to the values given
        For an existing instance, if is_primary was updated, it will be
        the only element of dictionary; otherwise will be an empty 
        dictionary.
        If is_primary is true, changes will also have an entry with
        the key 'primary_organization', and the subkey old will have
        the Organization which previously was primary for this Project
        as a value, and new for new.

        """
        created = False
        changes = {}
        qset = cls.objects.filter(
                organization=organization, user=user)

        if qset:
            # Existing OrganizationUser found
            obj = qset[0]
            old = obj.is_primary
            need2change = False
            if old is None:
                if is_primary is not None:
                    need2change = True
            else:
                if is_primary is None or is_primary != old:
                    need2change = True
            if need2change:
                if is_primary:
                    # If is_primary is set, we need to handle with care
                    # to avoid two primary organizations.
                    oldprimary = cls.set_primary_organization_for_user(
                           user=user, new=organization)
                    changes['primary_organization'] = {
                            'old':oldprimary, 'new':organization }
                else:
                    # If not is_primary, can just update field
                    obj.is_primary = is_primary
                    obj.save()
                changes['is_primary'] = { 'old':old, 'new':is_primary }
        else: #if qset
            # No previously existing object, create a new one
            created = True
            if is_primary:
                # Again, special handling
                oldprimary, obj = cls.set_primary_organization_for_user(
                       user=user, new=organization)
                changes['primary_organization'] = {
                        'old':oldprimary, 'new':organization }
            else:
                # Not is_primary, can just create
                obj = cls.objects.create(
                        user=user, 
                        organization=organization,
                        is_primary=is_primary)
            changes['user'] = user,
            changes['organization'] = organization,
            changes['is_primary'] = is_primary
        return obj, created, changes
    #end: def get_or_create_or_update_organization_user

    @classmethod
    def set_organizations_for_user(
            cls, user, organization_list, 
            delete=False, default_first_primary=False):
        """Updates the organizations associated with user from list

        Given an User and a list of Organizations, update 
        the Organizations associated with the Project.

        User can either be an User or an UserProfile instance.

        The elements of organization_list can be:
            a dict with keys 'organization' and 'is_primary'
                The value for the organization key can be an instance
                of Organization or the fullcode of an Organization
            an Organization instance
            the fullcode of an Organization.
        If the Organization was provided as instance or fullcode, or
        as a dictionary w/out the 'is_primary' key, is_primary will
        default to False *unless* default_first_primary is set AND
        it is the first element of the list.

        If is_primary is set, any previously primary Organization for
        the User (including if it was previously set by an earlier
        entry in this object list) is demoted to secondary and the
        current Organization is made primary.

        If delete is False (the default), the Organizations in
        organization_list are added to the set of Organizations for
        the User, and any previously existing Organizations for the
        user are left alone (with the exception that a primary Organization
        might be demoted to secondary if we added a new primary).
        If delete is True, any previously existing Organizations for the
        User not included in the organization_list will be disassociated
        with the User; i.e. the resulting set of Organizations will match
        organization_list.

        Returns a dictionary indicating changes made; keys are of the
        form 'Org[fcode]' where fcode is the fullcode of the Organization
        that was updated, and value is a dictionary with keys 'old' and 'new'.
        The old and new keys can have the following values:
            None: not present.  I.e., if in old it means the org was newly
                associated with the user, in new it means was disassociated.
            'primary': there is/was an entry with 'is_primary' flag true
            'secondary': there is/was an entry with 'is_primary' False
        """
        changes = {}
        keypattern = 'Org[{}]'
        # Convert user to an instance of UserProfile, if needed
        if isinstance(user, User):
            # Convert User to UserProfile
            userobj = user
            user = userobj.userprofile
        elif isinstance(user, UserProfile):
            # Already is, nothing to do
            pass
        else:
            raise ValueError('user must be an instance of User or UserProfile')

        if delete:
            # Delete flag set, we need the list of previously existing
            # Organizations
            qset = cls.objects.filter(user=user)
            previous_by_fullcode = {}
            fcodes2del = set()
            if qset:
                for rec in qset:
                    org = rec.organization
                    fcode = org.fullcode()
                    previous_by_fullcode[fcode] = rec
                    fcodes2del.add(fcode)

        first = default_first_primary
        for orec in organization_list:
            # Default is_primary to False, unless first iteration and default_first_primary
            is_primary = first
            first = False
            # Handle is orec is a dict
            if isinstance(orec, dict):
                # We got a dictionary
                tmporec = orec
                if 'organization' in tmporec:
                    orec = tmporec['organization']
                else:
                    raise ValueError('Dictionary elements of organization_list '
                            '*must* have an "organization" key')
                    if 'is_primary' in tmporec:
                        is_primary = tmporec['is_primary']
            # Get Organization from orec
            if isinstance(orec, Organization):
                # Already an Organization
                org = orec
            elif isinstance(orec, str):
                # Should be fullcode of an Organization
                org = Organization.get_organization_by_fullcode(orec)
            else:
                raise ValueError('Elements of organization_list must either be '
                        'an instance of Organization, a string with fullcode of '
                        'an Organization, or a dict with organization key with '
                        'instance or fullcode as value')

            # Add the Organization
            fcode = org.fullcode()
            key = keypattern.format(fcode)
            if fcode in previous_by_fullcode:
                # Organization already present for User, update is_primary as needed
                old = previous_by_fullcode[fcode]
                if old.is_primary != is_primary:
                    if is_primary:
                        # Handle primary orgs delicately
                        oldprimary, _ = cls.set_primary_organization_for_user(
                                user=user, new=org)
                        opkey = None
                        if oldprimary:
                            opkey = keypattern.format(oldprimary.fullcode())
                        if opkey in changes:
                            changes[opkey][new] = 'secondary'
                        else:
                            changes[opkey]={'old':'primary', 'new':'secondary'}
                        if key in changes:
                            changes[key][new] = 'primary'
                        else:
                            changes[key] = { 'old':None, 'new':'primary' }
                    else: #if is_primary
                        old.is_primary = False
                        old.save()
                        if key in changes:
                            changes[key][new] = 'secondary'
                        else:
                            changes[key] = { 'old':primary, 'new':'secondary' }
                    #end: if is_primary
                #end: if old.is_primary != is_primary
            else: #if fcode in previous_by_fullcode
                # Need to add
                if is_primary:
                    # Special care for primary orgs
                    oldprimary, _ = cls.set_primary_organization_for_user(
                            user=user, new=org)
                    opkey = None
                    if oldprimary:
                        opkey = keypattern.format(oldprimary.fullcode())
                    if opkey in changes:
                        changes[opkey][new] = 'secondary'
                    else:
                        changes[opkey]={'old':'primary', 'new':'secondary'}
                    if key in changes:
                        changes[key][new] = 'primary'
                    else:
                        changes[key] = { 'old':None, 'new':'primary' }
                else: #if is_primary:
                    cls.objects.create(
                            organization=org, user=user, is_primary=False)
                    if key in changes:
                        changes[key][new] = 'secondary'
                    else:
                        changes[key] = { 'old':None, 'new':'secondary' }
                #end: if is_primary:
            #end: if fcode in previous_by_fullcode

            # Remove our fullcode from list of those previously present
            fcodes2del.discard(fcode)
        #end: for orec

        if delete:
            # delete Organizations not on our list
            for fcode in fcodes2del:
                orgp = previous_by_fullcode[fcode]
                orgp.delete()
                if key in changes:
                    changes[key][new] = None
                else:
                    old = 'secondary'
                    if isprimary:
                        old = 'primary'
                    changes[key] = { 'old':old, 'new':None }

        return changes
    #end: def set_organizations_for_user

    @classmethod
    def delete_organizations_for_user(
            cls, user, organization_list, 
            ):
        """Deletes the organizations associated with user from list

        Given an User or UserProfile and a list of Organizations, disassociate the
        Organizations in the list from the User

        The elements of organization_list can be:
            a dict with keys 'organization' ('is_primary' can also
                be given, but is not used by this method)
                The value for the organization key can be an instance
                of Organization or the fullcode of an Organization
            an Organization instance
            the fullcode of an Organization.

        Returns a dictionary summarizing changes.  Key will be of the
        for Org[fcode], value will be a subdictionary with keys 'old' and
        'new':  'new' should always be None, 'old' can be 'primary' or
        'secondary' according to whether the orignal entry had 'is_primary'
        set or not
        """
        changes = {}
        keypattern = 'Org[{}]'
        # Convert user to an instance of UserProfile, if needed
        if isinstance(user, UserProfile):
            # Already is, nothing to do
            pass
        elif isinstance(user, User):
            # Convert User to UserProfile
            user = user.userprofile
        else:
            raise ValueError('user must be an instance of User or UserProfile')

        for orec in organization_list:
            # Handle is orec is a dict
            if isinstance(orec, dict):
                # We got a dictionary
                tmporec = orec
                if 'organization' in tmporec:
                    orec = tmporec['organization']
                else:
                    raise ValueError('Dictionary elements of organization_list '
                            '*must* have an "organization" key')
            # Get Organization from orec
            if isinstance(orec, Organization):
                # Already an Organization
                org = orec
            elif isinstance(orec, str):
                # Should be fullcode of an Organization
                org = Organization.get_organization_by_fullcode(orec)
            else:
                raise ValueError('Elements of organization_list must either be '
                        'an instance of Organization, a string with fullcode of '
                        'an Organization, or a dict with organization key with '
                        'instance or fullcode as value')

                # Delete the Organization from Project
                qset = cls.objects.filter(user=user, organization=org)
                if qset:
                    # Got a match
                    orgp = qset[0]
                    orgp = qset[0]
                    key = keypattern.format(orgp.fullcode())
                    old = 'secondary'
                    if orgp.is_primary:
                        old = 'primary'
                    orgp.delete()
                    changes[key] = { 'old':old, 'new':None }
        #end for orec in organization_list:
        return
    #end: def delete_organizations_for_user

#end: class OrganizationUser

class Directory2Organization(TimeStampedModel):
    """This table links strings in LDAP or similar directories to organizations.
    """
    organization = models.ForeignKey(
            Organization,
            on_delete=models.CASCADE, 
            null=False,
            blank=False,
        )
    directory_string = models.CharField(
            max_length=1024, 
            null=False,
            blank=False, 
            unique=True,
        )

    def __str__(self):
        return '{}=>{}'.format(self.directory_string,self.organization)
    #end: def __str__

    @classmethod
    def create_or_update_by_directory_string(
            cls, directory_string, organization):
        """Create or update an Directory2Organization with specified data
        
        We check if a Directory2Organization entry exists with the specified
        directory_string.  If yes, we update the organization to match
        what is specified, if needed.  Otherwise, we create a new entry
        for that directory_string and organization.

        organization can be either an Organization instance, or the full
        code of an Organization, or None (if None, any existing entry
        is deleted)

        Returns a triplet (obj, created, changes)
        where
            obj is the new or previously-existing Organization
            created is a boolean which is true if a new Org was created
            changes is a (possibly empty) indicating keyed on fields which
                were updated (if existing object updated), the value is 
                a dictionary with keys 'old' and 'new' giving the old and new
                values.
        """
        created = False
        changes = {}
        # First, coerce organization to an Organization
        org = organization
        if org is None:
            # None is allowed, nothing to do
            pass
        elif isinstance(org, Organization):
            # Already is, done
            pass
        elif isinstance(org, str):
            # Assume is a fullcode
            org = Organization.get_organization_by_fullcode(org)
        else:
            raise ValueError('organization must be None, an Organization, '
                    'or the fullcode of an Organization')
        #end: if org is None

        # Does an entry with this dirstring exist?
        qset = Directory2Organization.objects.filter(
                directory_string=directory_string)
        if qset:
            # An entry exists, update as needed
            obj = qset[0]
            old = obj.organization
            if org is None:
                # Special case: delete existing entry
                changes['organization'] = { 'old':old, 'new':None }
                obj.delete()
            elif old is None or old != org:
                # Need to change
                changes['organization'] = { 'old':old, 'new':org }
                obj.organization = org
                obj.save()
            #end: if org is None
        else: #if qset
            # Need to create new entry
            created = True
            obj = Directory2Organization.objects.create(
                    directory_string=directory_string,
                    organization=organization,
                )
            changes['organization'] = { 'old':None, 'new':org }
            changes['directory_string'] = { 
                    'old':None, 'new':directory_string }
        #end: if qset
        return obj, created, changes
    #end: def create_or_update_by_directory_string

    @classmethod
    def convert_strings_to_orgs(
            cls, 
            strings, 
            createUndefined=False, 
        ):
        """This class method takes a list of strings, and returns 
        a list of organizations.

        Strings should be a list of strings as returned by the 
        directory.  On success it will return a list of unique 
        Organizations corresponding to the strings.

        If a string is given which does not match any strings in 
        Directory2Organization, the behavior will depend on the 
        value of createUndefined.  If createUndefined is False, 
        the string will just be ignored.  If createUndefined is
        True, will call Organization.create_unknown_object_for_dir_string 
        and include it in the returned list.
        """
        tmporgs = set()
        for string in strings:
            qset = cls.objects.filter(directory_string=string)
            if qset:
                # Got an object, add it to tmporgs
                org = qset[0].organization
                tmporgs.add(org)
            else: #if qset
                # String did not match a known Directory2Object string
                if createUndefined:
                    # Create a placeholder organization
                    placeholder = \
                            Organization.create_unknown_object_for_dir_string(
                            string, dryrun)
                    tmporgs.add(placeholder)
                #end: if createUndefined
            #end: if qset:

        # Convert tmporgs set to list 
        orglist = list(tmporgs)
        return orglist
    #end: def convert_strings_to_orgs

    @classmethod
    def update_user_organizations_from_dirstrings(
            cls, 
            user, 
            dirstrings,
            delete=False, 
            createUndefined=False,
            include_nonselectable=False, 
            firstIsPrimary=False,
        ):
        """Updates the organizations associated with user from list
        of directory strings.

        Given an User/UserProfile instance and a list of 
        Directory2Organization directory_strings, updates the the 
        Organizations associated with the User.

        Basically, does convert_strings_to_orgs followed by
        OrganizationUser.set_organizations_for_user.  createUndefined
        is passed through to convert_strings_to_orgs, and delete is 
        passed through to set_organizations_for_user.  We return the return
        value from set_organizations_for_user.

        Normally, we filter the output of convert_strings_to_orgs to exclude
        those which do not have is_selectable_for_user set.  But if 
        include_nonselectable is set, we skip the filtering
        """
        orgs2add = cls.convert_strings_to_orgs(
                strings=dirstrings, 
                createUndefined=createUndefined,
            )
        if include_nonselectable:
            # Do not filter out orgs with is_selectable_for_user unset
            pass
        else:
            # Filter out orgs for which is_selectable_for_user is unset
            orgs2add = [ x for x in orgs2add if x.is_selectable_for_user ]
        #end: if include_nonselectable
        results = OrganizationUser.set_organizations_for_user(
                user=user, 
                organization_list=orgs2add, 
                delete=delete,
                default_first_primary=firstIsPrimary,
            )
        return results
    #end: def update_user_organizations_from_dirstrings

    @classmethod
    def update_project_organizations_from_dirstrings(
            cls, 
            project, 
            dirstrings,
            delete=False, 
            createUndefined=False,
            include_nonselectable=False, 
            firstIsPrimary=False,
        ):
        """Updates the organizations associated with project from list
        of directory strings.

        Given an Project instance and a list of Directory2Organization
        directory_strings, updates the the Organizations 
        associated with the Project.

        Basically, does convert_strings_to_orgs followed by
        OrganizationProject.set_organizations_for_project.  createUndefined
        is passed through to convert_strings_to_orgs, and delete is 
        passed through to set_organizations_for_project.  We return the return
        value from set_organizations_for_project.

        Normally, we filter the output of convert_strings_to_orgs to exclude
        those which do not have is_selectable_for_project set.  But if 
        include_nonselectable is set, we skip the filtering
        """
        orgs2add = cls.convert_strings_to_orgs(
                strings=dirstrings, 
                createUndefined=createUndefined,
            )
        if include_nonselectable:
            # Do not filter out orgs with is_selectable_for_project unset
            pass
        else:
            # Filter out orgs for which is_selectable_for_project is unset
            orgs2add = [ x for x in orgs2add if x.is_selectable_for_project ]
        #end: if include_nonselectable
        results = OrganizationProject.set_organizations_for_project(
                project=project, 
                organization_list=orgs2add, 
                delete=delete,
                default_first_primary=firstIsPrimary,
            )
        return results
    #end: def update_project_organizations_from_dirstrings

#end: class Directory2Organization

