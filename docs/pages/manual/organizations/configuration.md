# Configuration variables associated with the Organizational hierarchy code

This page discusses the configuration variables associated with the
[Organization](overview.md#orgs) hierarchy.

  - [Configuration variables related to UserProfiles](#user)
  - [Configuration variables related to Projects](#proj)
  - [Configuration variables related to LDAP Integration](#ldap)

These variables allow a fair degree of flexibility in
this addition to ColdFront.  Indeed, if you dislike it, you
can set the variables
  - [ORGANIZATION_USER_DISPLAY_MODE](#ORGANIZATION_USER_DISPLAY_MODE)
  - [ORGANIZATION_PROJECT_DISPLAY_MODE](#ORGANIZATION_PROJECT_DISPLAY_MODE)
  - [ORGANIZATION_PI_CAN_EDIT_FOR_PROJECT](#ORGANIZATION_PI_CAN_EDIT_FOR_PROJECT)
  - [ORGANIZATION_LDAP_AUTH_POPULATE_USER_ORGANIZATIONS](#ORGANIZATION_LDAP_AUTH_POPULATE_USER_ORGANIZATIONS)
all to false, and the Organizational hierarchy additions 
mostly go away --- the (presumably empty) models will still
appear in the ColdFront Admin pages, (including on the UserProfile
and Project Admin pages), but will not show up to end users.

The configuration variables can be set in a `local_settings.py` file,
or in a `coldfront.env` file, or simple set as environmental variables
for the process running ColdFront.

**NOTE:** A number of the variables take Boolean values.  If setting
them as environmental variables (either directly or via `coldfront.env`
or the like), it is *strongly* recommended you set the variable to
1 for True or 0 for False.

## Configuration variables related to UserProfiles {#user}

The following configuration variables control how the 
[Organization](overview.md#orgs)
hierarchy structure is displayed on User and UserProfile pages.

Admins will always be able to see and update the Organizations for an
User on either the UserProfile admin page, or in the Organization admin
page.

### ORGANIZATION_USER_DISPLAY_MODE {#ORGANIZATION_USER_DISPLAY_MODE)

This variable determines if a list of Organizations the User belongs 
to will be displayed on the UserProfile page of an User.  It recognizes 
three values:
    - True (1 in environmental variables): Always display 
    - False (0 in environmental variables): Never display 
    - 'not-empty': Only display if there are Organizations to display

The default value is 'not-empty'.

**NOTE**: The [Organizations](overview.md#orgs) displayed are filtered, so
only Organizations with the `is_selectable_for_user` flag set will be 
displayed, even if the User belongs to other Organizations.  
The `not-empty` variant bases the decision on whether any Organizations
are found _after_ filtering.

### ORGANIZATION_USER_DISPLAY_TITLE {#ORGANIZATION_USER_DISPLAY_TITLE}

This variable should be a text string which will be used as a label
for the [Organization](overview.md@orgs) entry on the UserProfile page 
of an User.  The default value is `Departments(s), etc.`.

This variable is effectively ignored if 
ORGANIZATION_USER_DISPLAY_MODE(#ORGANIZATION_USER_DISPLAY_MODE)
is False, or if it is `not-empty` and the User does not belong to any
selectable Organizations.

## Configuration variables related to Projects {#proj}

The following configuration variables control how the Organization
hierarchy structure is displayed on the Project pages.

Admins will always be able to see and update the Organizations for an
User on either the UserProfile admin page, or in the Organization admin
page.

### ORGANIZATION_PROJECT_DISPLAY_MODE {#ORGANIZATION_PROJECT_DISPLAY_MODE}

This variable determines if a list of Organizations the User belongs 
to will be displayed on the UserProfile page of an User.  It recognizes 
three values:
    - True (1 in environmental variables): Always display 
    - False (0 in environmental variables): Never display 
    - 'not-empty': Only display if there are Organizations to display

The default value is 'not-empty'.

**NOTE**: The [Organizations](overview.md#orgs) displayed are filtered, so
only Organizations with the `is_selectable_for_project` flag set will be 
displayed, even if the Project belongs to other Organizations.  
The `not-empty` variant bases the decision on whether any Organizations
are found _after_ filtering.


### ORGANIZATION_PI_CAN_EDIT_FOR_PROJECT {#ORGANIZATION_PI_CAN_EDIT_FOR_PROJECT}

This variable determines whether the PI/managers for a Project can edit
the [Organizations](overview.md@orgs) to which the Project belongs.  It
takes Boolean variables (True/False in python, or 1/0 when set as an 
environmental variable). 

The default value is True.

**NOTE**: The [Organizations](overview.md#orgs) displayed are filtered, so
only Organizations with the `is_selectable_for_project` flag set will be 
seen and only such Organizations will be selectable by the PI.

### ORGANIZATION_PROJECT_DISPLAY_TITLE {#ORGANIZATION_PROJECT_DISPLAY_TITLE}

This variable should be a text string which will be used as a label
for the [Organization](overview.md@orgs) entry on the pages 
for a Project.  The default value is `Departments(s), etc.`.

This variable is effectively ignored if 
ORGANIZATION_PROJECT_DISPLAY_MODE(#ORGANIZATION_PROJECT_DISPLAY_MODE)
is False, or if it is `not-empty` and the Project does not belong to any
selectable Organizations.

## Configuration variables related to LDAP Integration {#ldap}

The following variables are for configuring the 
[integration of Organizations with LDAP](ldap.md).
They are ignored unless either the 
[LDAP User Search](https://github.com/ubccr/coldfront/tree/master/coldfront/plugins/ldap_user_search)
plugin or the LDAP Auth plugin are enabled.

### ORGANIZATION_LDAP_AUTH_POPULATE_USER_ORGANIZATIONS {#ORGANIZATION_LDAP_AUTH_POPULATE_USER_ORGANIZATIONS}

This configuration variable determines whether the 
[Organizations](overview.md#orgs) for an User are updated whenever the User
logs in using the LDAP Auth plugin.  It accepts Boolean values; True/False
in python, or 1/0 when setting via environmental variables.

The default value is False, meaning there is no automatic update of the
Organizations to which an User belongs when the log in via LDAP Auth.

If it is set, and the 
ORGANIZATION_LDAP_USER_ATTRIBUTE(#ORGANIZATION_LDAP_USER_ATTRIBUTE)
variable is set appropriately, then when an User logs in via the LDAP Auth
plugin, ColdFront will also collect a list of strings from the LDAP_user
attribute with the name ORGANIZATION_LDAP_USER_ATTRIBUTE will be collected,
and mapped onto existing Organizations via the 
[Directory2Organization](ldap.md#dir2orgs) table, and those Organizations
will be added to the UserProfile.  The configuration variables
    - ORGANIZATION_LDAP_USER_ATTRIBUTE(#ORGANIZATION_LDAP_USER_ATTRIBUTE)
    - ORGANIZATION_LDAP_USER_ADD_PARENTS(#ORGANIZATION_LDAP_USER_ADD_PARENTS)
    - ORGANIZATION_LDAP_USER_CREATE_PLACEHOLDERS(#ORGANIZATION_LDAP_USER_CREATE_PLACEHOLDERS)
    - ORGANIZATION_LDAP_USER_DELETE_MISSING(#ORGANIZATION_LDAP_USER_DELETE_MISSING)
control how that is done.

### ORGANIZATION_LDAP_USER_ATTRIBUTE {#ORGANIZATION_LDAP_USER_ATTRIBUTE}

The configuration variable provides the name of the LDAP attribute of an
LDAP user which will be examined to determine what 
[Organizations](overview.md#orgs) the User belongs to.  The attribute should
return a list of strings which get mapped to Organizations within ColdFront
via the [Directory2Organization](ldap.pm#dir2orgs) table.

This variable is used both for the 
[integration with LDAP Auth plugin](ldap.pm#ldapauth) and for the 
[integration with LDAP User Search plugin](ldap.pm#ldapsearch).

The default value is None, which prevents integration with either LDAP plugin.

If this variable is not set, a True value for 
ORGANIZATION_LDAP_AUTH_POPULATE_USER_ORGANIZATIONS {#ORGANIZATION_LDAP_AUTH_POPULATE_USER_ORGANIZATIONS}
is ignored.

### ORGANIZATION_LDAP_USER_ADD_PARENTS {#ORGANIZATION_LDAP_USER_ADD_PARENTS}

This configuration variable determines whether the Organization and LDAP
integration methods will cause the addition of ancestors of the 
[Organizations](overview.md#orgs) received from LDAP for the user.
It accepts Boolean values; True/False
in python, or 1/0 when setting via environmental variables.

The default value is False.

This variable is only used with the LDAP Auth plugin; the
[update_user_organizations_from_ldap](mcdline.md#update_user_organizations_from_ldap)
command has a flag which behaves similarly but does not depend on this
configuration variable.

If this variable is True, and an user is having his/her Organization list
updated after logging in via the LDAP Auth plugin, this will cause the
ancestors of any Organization obtained for the User from LDAP to also be
added to the User.

For example, assume User `joe` logs in via the LDAP Auth plugin, and is having
his Organizations updated from LDAP.  If one of the strings returned 
by the attribute named
[ORGANIZATION_LDAP_USER_ATTRIBUTE](#ORGANIZATION_LDAP_USER_ATTRIBUTE)
corresponds to an Organization with `fullcode` "UMD-CMNS-CHEM", normally
only the "UMD-CMNS-CHEM" will be associated with the UserProfile (if needed).
If this variable is set to True, then it would add the Organizations
"UMD-CMNS-CHEM", "UMD-CMNS" and "UMD" to the UserProfile.

This could prove useful if one desires all UserProfiles who belong to children
of an Organization to also be explicitly listed as members of the parent.
However, one can usually get the same result by having the queries for an
Organization also query all of the descendents of the Organization.  It is
also problematic as it only effects additions via the LDAP Auth plugin.
Administrators can add Users to Organizations without adding the parents,
and/or can delete the parent Organizations from an User.

### ORGANIZATION_LDAP_USER_CREATE_PLACEHOLDERS {#ORGANIZATION_LDAP_USER_CREATE_PLACEHOLDERS}

This configuration variable accepts Boolean values; True/False
in python, or 1/0 when setting via environmental variables.

This configuration variable controls the behavior when, while updating the
Organizations to which an User belongs after the User logs in via the
LDAP Auth plugin, a string from the 
[ORGANIZATION_LDAP_USER_ATTRIBUTE](#ORGANIZATION_LDAP_USER_ATTRIBUTE)
attribute is not found in the [Directory2Organization](ldap.md#dir2orgs)
table.

Normally in such situations, the LDAP string is just ignored.  If this
variable is set, a 
[placeholder Organization is created and associated with the user](ldap.md#placeholder).

The default value is True.

This variable is only used with the LDAP Auth plugin; the
[update_user_organizations_from_ldap](mcdline.md#update_user_organizations_from_ldap)
command has a flag which behaves similarly but does not depend on this
configuration variable.

### ORGANIZATION_LDAP_USER_DELETE_MISSING {#ORGANIZATION_LDAP_USER_DELETE_MISSING}

This configuration variable accepts Boolean values; True/False
in python, or 1/0 when setting via environmental variables.

This configuration variable controls the behavior when updating the
Organizations to which an User belongs after the User logs in via the
LDAP Auth plugin. In particular, how to handle [Organizations](overview.md#orgs)
to which the User belong which do not correspond to any Organizations obtained
(after mapping through [Directory2Organization](ldap.md#dir2orgs), etc.)
from LDAP.  
[ORGANIZATION_LDAP_USER_ATTRIBUTE](#ORGANIZATION_LDAP_USER_ATTRIBUTE)
attribute is not found in the [Directory2Organization](ldap.md#dir2orgs)
table.

Normally, the process of updating Organizations for an User from LDAP is
an additive process only; i.e. any Organizations which LDAP claims the
User in question belongs to are added to the User if needed.  

If this configuration variable is set, then we effectively disassociate all
Organizations from the User before adding back the Organizations from LDAP.

The default value is False.

This variable is only used with the LDAP Auth plugin; the
[update_user_organizations_from_ldap](mcdline.md#update_user_organizations_from_ldap)
command has a flag which behaves similarly but does not depend on this
configuration variable.

