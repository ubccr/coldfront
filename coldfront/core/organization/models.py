import sys

from django.db import models
from model_utils.models import TimeStampedModel
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db.models import Q

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
            unique=True)
    level = models.IntegerField(
            null=False, 
            blank=False, 
            unique=True,
            help_text='The lower this value, the higher this type is in '
                'the organization.')
    parent = models.OneToOneField(
            'self', 
            on_delete=models.CASCADE, 
            null=True, 
            blank=True)

    def __str__(self):
        return self.name

    def clean(self):
        """Validation: ensure our parent has a higher level than us

        If we have a parent, make sure it has a higher level than us.
        If we do not have a parent, make sure there are no other rows
        in table. (UNIQUE on parent does not work, as SQL allows multiple
        rows with NULL for an UNIQUE field).
        """
        # First, call base class's version
        super().clean()
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
        else:
            # No parent, make sure we are the highest level in table
            count = OrganizationLevel.objects.count()
            if count > 0:
                raise ValidationError( 'OrganizationLevel {}, level={} '
                    'has no parent, but {} other rows in table' .format(
                        self, self.level, count))


        return

    def save(self, *args, **kwargs):
        """Override save() to call full_clean first"""
        self.full_clean()
        return super(OrganizationLevel, self).save(*args, **kwargs)
                
    def root_organization_level():
        """Returns the 'root' OrganizationLevel, ie orglevel w/out parent.

        Returns the root OrganizationLevel if found (first found), or
        None if none found.
        """
        qset = OrganizationLevel.objects.filter(parent__isnull=True)
        if qset:
            return qset[0]
        else:
            return None

    def child_organization_level(self):
        """Returns the OrganizationLevel whose parent is self.

        Returns None if no child found.
        """
        qset = OrganizationLevel.objects.filter(parent=self)
        if qset:
            return qset[0]
        else:
            return None

    class Meta:
        ordering = ['-level']

class Organization(TimeStampedModel):
    """This represents an organization, in a multitiered hierarchy.

    All organizational units, regardless of level are stored in this
    table.  Each links back to a specific OrganizationLevel, and can
    (and will unless at the highest organizational level) have a 
    parent which belongs to a higher organizational level.
    """
    
    parent = models.ForeignKey(
            'self', 
            on_delete=models.CASCADE, 
            null=True, 
            blank=True)
    organization_level = models.ForeignKey(
            OrganizationLevel, 
            on_delete=models.CASCADE, 
            null=False)
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
                ])
    shortname = models.CharField(
            max_length=1024, 
            null=True, 
            blank=False, 
            unique=False,
            help_text='A medium length name for this organization, used '
                'in many displays.')
    longname = models.CharField(
            max_length=2048, 
            null=True, 
            blank=False, 
            unique=False,
            help_text='The full name for this organization, for official '
                'contexts')
    is_selectable_for_user = models.BooleanField(
            default=True,
            help_text='This organization can be selected for Users')
    is_selectable_for_project = models.BooleanField(
            default=True,
            help_text='This organization can be selected for Projects')

    def __str__(self):
        return self.shortname

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

    def save(self, *args, **kwargs):
        """Override save() to call full_clean first"""
        self.full_clean()
        return super(Organization, self).save(*args, **kwargs)

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
                
    def fullcode(self):
        """Returns a full code, {parent_code}-{our_code}."""
        retval = self.code
        if self.parent:
            retval = '{pcode}-{code}'.format(
                    pcode=self.parent.fullcode(),
                    code=retval)
        return retval

    def semifullcode(self):
        """Returns full code of our parent, hyphen, our short name."""
        retval = self.shortname
        if self.parent:
            retval = '{pcode}-{code}'.format(
                    pcode=self.parent.fullcode(),
                    code=retval)
        return retval

    def __str__(self):
        return self.fullcode()

    def get_organization_by_fullcode(fullcode):
        """Class method which returns organization with given fullcode.

        This will get the Organization with the given full code. If such
        an Organization object is found, returns it.  Returns None if not
        found.
        """
        codes = fullcode.split('-')
        lastcode = codes[-1]
        orgs = Organization.objects.filter(code__exact=lastcode)
        for org in orgs:
            if org.fullcode() == fullcode:
                return org
        return None

    def get_or_create_unknown_main(dryrun=False):
        """This returns a 'top-level' Unknown organization.

        It will look for one, and return if found.  If not found,
        creates one.

        If dryrun is set, will not actually create an instance but
        just return None
        """
        qset = Organization.objects.filter(code='Unknown', parent__isnull=True)
        if qset:
            # We got an org with code='Unknown', return first found
            return qset[0]

        if dryrun:
            return None
        #Not found, create one
        orglevel = OrganizationLevel.root_organization_level()
        if not orglevel:
            raise OrganizationLevel.DoesNotExist('No parentless OrganizationLevel found')
        new = Organization.objects.create(
                code='Unknown',
                parent=None,
                organization_level=orglevel,
                shortname='Unknown',
                longname='Container for Unknown organizations'
                )
        return new

    def create_unknown_object_for_dir_string(dirstring, dryrun=False):
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
        unknown_main = Organization.get_or_create_unknown_main(dryrun)
        orglevel = None
        if unknown_main is not None:
            main_orglevel = unknown_main.organization_level
            orglevel = main_orglevel.child_organization_level()
        placeholder = Organization(
            code='Unknown_placeholder',
            parent=unknown_main,
            organization_level=orglevel,
            shortname='Unknown: {}'.format(dirstring),
            longname='Unknown: {}'.format(dirstring),
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
    
    def convert_strings_to_orgs(strings, createUndefined=False,
            dryrun=False):
        """This class method takes a list of strings, and returns 
        a list of organizations.

        Strings should be a list of strings as returned by the 
        directory.  On success it will return a list of unique 
        Organizations corresponding to the strings.

        If a string is given which does not match any strings in 
        Directory2Organization, the behavior will depend on the 
        value of createUndefined.  If createUndefined is False, 
        the string will just be ignored.  If createUndefined is
        True, will call create_unknown_object_for_dir_string and
        include it in the returned list.
        """
        tmporgs = set(())
        for string in strings:
            qset = Directory2Organization.objects.filter(
                directory_string=string)
            if qset:
                # Got an object, add it to tmporgs
                org = qset[0].organization
                tmporgs |= { org }
                continue
            # String did not match a known Directory2Object string
            if not createUndefined:
                # Just ignore it
                continue
            # Create a placeholder organization
            placeholder = \
                    Organization.create_unknown_object_for_dir_string(
                    string, dryrun)
            tmporgs |= { placeholder }

        # Convert tmporgs set to list 
        orglist = list(tmporgs)
        return orglist

    def add_parents_to_organization_list(organizations):
        """Given a list of organizations, append to the list
        any ancestor organizations to the list.

        Returns the augmented list of Organizations
        """
        tmporgs = set(organizations)
        # Add all ancestors to tmporgs set
        for org in organizations:
            ancestors = org.ancestors()
            tmporgs |= set(ancestors)
        # Now find what was added and append to the list
        toadd = tmporgs - set(organizations)
        return organizations +list(toadd)

    def update_user_organizations(user, organizations,
            addParents=False, delete=False, dryrun=False):
        """Updates the organizations associated with user from list
        of Organizations.

        Given an UserProfile and a list of Organizations, update 
        the Organizations associated with the UserProfile.

        Return value is dictionary with keys 'added' and 'removed',
        the values for which are lists of Organization objects
        which were added/removed from the user.

        If addParents is set, will include the ancestors of any
        Organizations in the list as well.
        If delete is set, will disassociated from the UserProfile
        and Organizations not in the (possible augmented with
        parents) Organizations list.
        If dryrun is set, does not actually add/remove Organizations, 
        but still returns as if it did.
        """
        orgs2add = organizations
        if addParents:
            orgs2add = Organization.add_parents_to_organization_list(
                    orgs2add)
        orgs2add = set(orgs2add)

        # Handle special case when (in dryrun) we are given an user
        # who has not been saved to DB yet.  Should only be for dryrun
        oldorgset = set()
        if user.id is not None:
            oldorgset = set(user.organizations.all())
        neworgs = orgs2add - oldorgset
        if not dryrun:
            for org in list(neworgs):
                user.organizations.add(org)

        orgs2del = oldorgset - orgs2add
        orgs2del = list(orgs2del)
        if delete:
            if not dryrun:
                for org in orgs2del:
                    user.organizations.remove(org)
        return {'added': neworgs, 'removed': orgs2del }

    def update_project_organizations(project, organizations,
            addParents=False, delete=False, dryrun=False):
        """Updates the organizations associated with project from list
        of Organizations.

        Given an Project and a list of Organizations, update 
        the Organizations associated with the Project.

        Return value is dictionary with keys 'added' and 'removed',
        the values for which are lists of Organization objects
        which were added/removed from the project.

        If addParents is set, will include the ancestors of any
        Organizations in the list as well.
        If delete is set, will disassociated from the UserProfile
        and Organizations not in the (possible augmented with
        parents) Organizations list.
        If dryrun is set, does not actually add/remove Organizations, 
        but still returns as if it did.
        """
        orgs2add = organizations
        if addParents:
            orgs2add = Organization.add_parents_to_organization_list(
                    orgs2add)
        orgs2add = set(orgs2add)
        oldorgset = set(project.organizations.all())
        neworgs = orgs2add - oldorgset
        if not dryrun:
            for org in list(neworgs):
                project.organizations.add(org)

        orgs2del = oldorgset - orgs2add
        orgs2del = list(orgs2del)
        if delete:
            if not dryrun:
                for org in orgs2del:
                    project.organizations.remove(org)
        return { 'added': neworgs, 'removed': orgs2del }

    def update_user_organizations_from_dirstrings(
            user, dirstrings, addParents=False, 
            delete=False, createUndefined=False,
            dryrun=False):
        """Updates the organizations associated with user from list
        of directory strings.

        Given an UserProfile and a list of Directory2Organization
        directory_strings, updates the the Organizations 
        associated with the UserProfile.

        Like update_user_organizations, returns a dictionary with 
        keys 'added' and 'removed' with lists of Organization objects
        added/removed.

        Basically, does convert_strings_to_orgs followed by
        update_user_organizations.  addParents, delete, and dryrun passed
        to update_user_organizations, and createUndefined to
        convert_strings_to_orgs.
        """
        orgs2add = Organization.convert_strings_to_orgs(
                strings=dirstrings, 
                createUndefined=createUndefined,
                dryrun=dryrun)
        results = Organization.update_user_organizations(
                user=user, 
                organizations=orgs2add, 
                addParents=addParents, 
                delete=delete,
                dryrun=dryrun)
        return results

    def update_project_organizations_from_dirstrings(
            project, dirstrings, addParents=False, 
            delete=False, createUndefined=False, dryrun=False):
        """Updates the organizations associated with project from list
        of directory strings.

        Given an Project and a list of Directory2Organization
        directory_strings, updates the the Organizations 
        associated with the Project.

        Basically, does convert_strings_to_orgs followed by
        update_project_organizations.  addParents, delete, and dryrun passed
        to update_project_organizations, and createUndefined to
        convert_strings_to_orgs.
        """
        orgs2add = Organization.convert_strings_to_orgs(
                dirstrings, createUndefined)
        results = Organization.update_project_organizations(
                project=project, 
                organizations=orgs2add, 
                addParents=addParents, 
                delete=delete,
                dryrun=dryrun,
                )
        return results

    class Meta:
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

class Directory2Organization(TimeStampedModel):
    """This table links strings in LDAP or similar directories to organizations.
    """
    organization = models.ForeignKey(
            Organization,
            on_delete=models.CASCADE, 
            null=False,
            blank=False)
    directory_string = models.CharField(
            max_length=1024, 
            null=False,
            blank=False, 
            unique=True)

    def __str__(self):
        return '{}=>{}'.format(self.directory_string,self.organization)


