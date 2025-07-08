# project_openldap management commands

This directory contains django management commands:

- **project_openldap_check_setup** - to aid setup of the plugin, before going into production, check for valid project\_openldap plugin setup. It will check the type and bounds of variables to provide confidence.
- **project_openldap_sync** - to check the state of both the Coldfront (django) and OpenLDAP project definitions (in terms of status, membership). This operates on project statuses New,Active,Archived. It will loop all project_groups or a specific group.

**NOTE: Coldfront (django) is always assumed the source of truth.**

**NOTE: See the ``Mermaid.md`` file for a mermaid diagram of the main function within project_openldap_sync**

# Usage

The commands can be executed by using the coldfront user inside the **venv**:

Check for valid project_openldap plugin setup:

- ```coldfront project_openldap_check_setup [options]```

Check the state of both the Coldfront (django) and OpenLDAP projects:

- ```coldfront project_openldap_sync [options]```

In both cases use ``--help`` for options.


## project_openldap_sync - example command usage

**NOTE: Detailed examples are shown at the bottom of this README.md**

Check, but don't sync project group/code CDF0005.

- ``coldfront project_openldap_sync -p CDF0005``

Check AND sync project group/code CDF0005. Sync is required to write changes via the bind user to OpenLDAP.

- ``coldfront project_openldap_sync -p CDF0005 -s``

Check ALL but don't sync.

- ``coldfront project_openldap_sync -a``

Check ALL but AND sync. Sync is required to write changes via the bind user to OpenLDAP.

- ``coldfront project_openldap_sync -a -s``


If you need to write a project to the archive_ou, then both ``-z (--writearchive)`` and ``-s (--sync)`` are required.

E.g. If project CDF0003 is not in the archive ou but is archived in CF Django, then use both options:

- ``coldfront project_openldap_sync -p CDF0005 -s -z``

## project_openldap_sync - usage: skip archived projects

Its possible to skip Coldfront django projects with archived status in the sync management command by supplying ``-x`` or ``--skip_archived``.


# project_openldap_sync - Other:

## If a project needs added by the sync management command

If a project needs added to OpenLDAP. One pass of the sync management command is required to add.

Subsequently a second pass will be required to process membership.

## Update an archived (archived in OpenLDAP) project membership

If for some reason an archived project in OpenLDAP doesn't have the correct membership (vs the Coldfront django archived project), the sync management command should correct it. Though ``-z`` or ``--writearchive`` will need supplied. This is a corner case, and unlikely to arise.

## Updating the OpenLDAP description field.

This is done using the ``-d`` or ``--update_description`` option. No checks are performed for this. It will attempt to update the description filed regardless.

This can either be used with loop all or against a specific project.


## Real examples from testing and dev work

### Scenario 1 - missing user in a project

- Only 1x project is present but loop all projects was used
- It was detected that _ldapuser2_ was missing in OpenLDAP
- Notification is received that we need to apply sync to make changes

**Action:** Check status using loop all (``-a``).

```
(coldfront_venv) [coldfront@coldfront coldfront]$ coldfront project_openldap_sync -a
Syncing ALL OpenLDAP groups with ColdFront
--------------------
processing Project CDF0001

search project OU result: True
search project archive OU result: False
Project CDF0001 is a new or active project - found cn=CDF0001,ou=CDF0001,ou=projects,dc=coldfront,dc=ac,dc=uk
Users are MISSING in OpenLDAP - ADDITION ACTION (OpenLDAP): cn=CDF0001,ou=CDF0001,ou=projects,dc=coldfront,dc=ac,dc=uk
 ('ldapuser2',)
sync is required to make changes, please supply: -s or --sync
```

**Outcome:** Missing user identified, notified need sync to make the change.

**Next action:** Apply sync (``-s``) to make changes to this non-archive project.

```
(coldfront_venv) [coldfront@coldfront coldfront]$ coldfront project_openldap_sync -a  -s 
Enabling writes - Syncing OpenLDAP with ColdFront
Syncing ALL OpenLDAP groups with ColdFront
--------------------
processing Project CDF0001

search project OU result: True
search project archive OU result: False
Project CDF0001 is a new or active project - found cn=CDF0001,ou=CDF0001,ou=projects,dc=coldfront,dc=ac,dc=uk
Users are MISSING in OpenLDAP - ADDITION ACTION (OpenLDAP): cn=CDF0001,ou=CDF0001,ou=projects,dc=coldfront,dc=ac,dc=uk
 ('ldapuser2',)
SYNC True - Added members ('ldapuser2',)
```


### Scenario 2 - mix of project status - OpenLDAP out of sync with Coldfront

- project 1 is archived but OpenLDAP is not aware.
- project 2 is missing from OpenLDAP and is a normal project.
- project 3 is missing from OpenLDAP and is an archived project.
- project 4 is missing from OpenLDAP and is a normal project.

NOTE: coldfront PI usage is due to test/dev (projects were created as coldfront user). This wouldn't be the case in production...

Run loop all (``-a``) to check state.

```
(coldfront_venv) [coldfront@coldfront coldfront]$ coldfront project_openldap_sync -a 
Syncing ALL OpenLDAP groups with ColdFront
--------------------
processing Project CDF0001

search project OU result: True
search project archive OU result: False
ou=CDF0001,ou=projects,dc=coldfront,dc=ac,dc=uk <<< WARNING WE EXPECTED THIS TO BE ARCHIVED IN OPENLDAP - PROJECT_OPENLDAP_ARCHIVE_OU is set
cn=CDF0001,ou=CDF0001,ou=archive_projects,dc=coldfront,dc=ac,dc=uk is the expected DN
Project CDF0001 - Corrective action may be required
--------------------
processing Project CDF0002

search project OU result: False
search project archive OU result: False
Project DN for CDF0002 is MISSING from OpenLDAP - SYNC is False - WILL NOT WRITE TO OpenLDAP
--------------------
processing Project CDF0003

search project OU result: False
search project archive OU result: False
cn=CDF0003,ou=CDF0003,ou=projects,dc=coldfront,dc=ac,dc=uk <<< WARNING WE EXPECTED THIS TO BE ARCHIVED IN OPENLDAP - PROJECT_OPENLDAP_ARCHIVE_OU is set
cn=CDF0003,ou=CDF0003,ou=archive_projects,dc=coldfront,dc=ac,dc=uk is the expected DN
Project CDF0003 - Corrective action may be required
--------------------
processing Project CDF0004

search project OU result: False
search project archive OU result: False
Project DN for CDF0004 is MISSING from OpenLDAP - SYNC is False - WILL NOT WRITE TO OpenLDAP
```

**Outcome:** We see changes are required in OpenLDAP...

**Next action:** Apply ``-s`` to sync.

```
(coldfront_venv) [coldfront@coldfront coldfront]$ coldfront project_openldap_sync -a -s
Enabling writes - Syncing OpenLDAP with ColdFront
Syncing ALL OpenLDAP groups with ColdFront
--------------------
processing Project CDF0001

search project OU result: True
search project archive OU result: False
Project DN ou=CDF0001,ou=projects,dc=coldfront,dc=ac,dc=uk needs moved to Archive OU, with DN cn=CDF0001,ou=CDF0001,ou=archive_projects,dc=coldfront,dc=ac,dc=uk - Requires writing to archive OU
WRITE_TO_ARCHIVE is required to make changes, please supply: -z or --writearchive
--------------------
processing Project CDF0002

search project OU result: False
search project archive OU result: False
Adding OpenLDAP project OU entry - DN: ou=CDF0002,ou=projects,dc=coldfront,dc=ac,dc=uk
Adding OpenLDAP project posixgroup entry - DN: cn=CDF0002,ou=CDF0002,ou=projects,dc=coldfront,dc=ac,dc=uk
Adding OpenLDAP project posixgroup entry - GID: 8002
Adding OpenLDAP project posixgroup entry - GID: INSTITUTE: CardiffUniversity | PI: coldfront | TITLE: cf project 2
--------------------
processing Project CDF0003

search project OU result: False
search project archive OU result: False
cn=CDF0003,ou=CDF0003,ou=archive_projects,dc=coldfront,dc=ac,dc=uk Needs written to archive OU
WRITE_TO_ARCHIVE is required to make changes, please supply: -z or --writearchive
--------------------
processing Project CDF0004

search project OU result: False
search project archive OU result: False
Adding OpenLDAP project OU entry - DN: ou=CDF0004,ou=projects,dc=coldfront,dc=ac,dc=uk
Adding OpenLDAP project posixgroup entry - DN: cn=CDF0004,ou=CDF0004,ou=projects,dc=coldfront,dc=ac,dc=uk
Adding OpenLDAP project posixgroup entry - GID: 8004
Adding OpenLDAP project posixgroup entry - GID: INSTITUTE: CardiffUniversity | PI: coldfront | TITLE: cf project 4
```

**Outcome:**
- Projects with _New_ or _Active_ status are written.
- We are warned we need write archive to perform actions relating to the archive ou. These are to move (existing project1) or create project directly in archive (project3). Only the sync management command will create a project directly to archive.

**Next action:** Supply ``-z`` to writearchive...


```
(coldfront_venv) [coldfront@coldfront coldfront]$ coldfront project_openldap_sync -a -s -z
Enabling writes - Syncing OpenLDAP with ColdFront
Syncing ALL OpenLDAP groups with ColdFront
--------------------
processing Project CDF0001

search project OU result: True
search project archive OU result: False
Moving project to archive OU, DN: cn=CDF0001,ou=CDF0001,ou=archive_projects,dc=coldfront,dc=ac,dc=uk in OpenLDAP - SYNC is True - WRITING TO Openldap
--------------------
processing Project CDF0002

search project OU result: True
search project archive OU result: False
Project CDF0002 is a new or active project - found cn=CDF0002,ou=CDF0002,ou=projects,dc=coldfront,dc=ac,dc=uk
NOTIFICATION: There are 0 Coldfront (django) project members which could be added to OpenLDAP for this project
NOTIFICATION: Both Coldfront django and OpenLDAP have 0 members - no action to take by sync_members
--------------------
processing Project CDF0003

search project OU result: False
search project archive OU result: False
Adding archived project cn=CDF0003,ou=CDF0003,ou=archive_projects,dc=coldfront,dc=ac,dc=uk to OpenLDAP - SYNC is True - WRITING TO Openldap
Adding OpenLDAP project archive OU entry - DN: ou=CDF0003,ou=archive_projects,dc=coldfront,dc=ac,dc=uk
Adding OpenLDAP project archive posixgroup entry - DN: cn=CDF0003,ou=CDF0003,ou=archive_projects,dc=coldfront,dc=ac,dc=uk
--------------------
processing Project CDF0004

search project OU result: True
search project archive OU result: False
Project CDF0004 is a new or active project - found cn=CDF0004,ou=CDF0004,ou=projects,dc=coldfront,dc=ac,dc=uk
NOTIFICATION: There are 0 Coldfront (django) project members which could be added to OpenLDAP for this project
NOTIFICATION: Both Coldfront django and OpenLDAP have 0 members - no action to take by sync_members
```

**Outcome:**

- Now we see above archived projects got written (projects 1,3), we also see 0 membership notification on project (2,4).
- If we check once more with loop all, we'll also see that for the archive projects. Those weren't checked as the last pass required a project move or project addition direct to archive.

**Next action:** loop all (``-a``)

```
(coldfront_venv) [coldfront@coldfront coldfront]$ coldfront project_openldap_sync -a
Syncing ALL OpenLDAP groups with ColdFront
--------------------
processing Project CDF0001

search project OU result: False
search project archive OU result: True
Project CDF0001 is an archived project - found cn=CDF0001,ou=CDF0001,ou=archive_projects,dc=coldfront,dc=ac,dc=uk
--------------------
processing Project CDF0002

search project OU result: True
search project archive OU result: False
Project CDF0002 is a new or active project - found cn=CDF0002,ou=CDF0002,ou=projects,dc=coldfront,dc=ac,dc=uk
NOTIFICATION: There are 0 Coldfront (django) project members which could be added to OpenLDAP for this project
NOTIFICATION: Both Coldfront django and OpenLDAP have 0 members - no action to take by sync_members
--------------------
processing Project CDF0003

search project OU result: False
search project archive OU result: True
Project CDF0003 is an archived project - found cn=CDF0003,ou=CDF0003,ou=archive_projects,dc=coldfront,dc=ac,dc=uk
NOTIFICATION: There are 0 Coldfront (django) project members which could be added to OpenLDAP for this project
NOTIFICATION: Both Coldfront django and OpenLDAP have 0 members - no action to take by sync_members
--------------------
processing Project CDF0004

search project OU result: True
search project archive OU result: False
Project CDF0004 is a new or active project - found cn=CDF0004,ou=CDF0004,ou=projects,dc=coldfront,dc=ac,dc=uk
NOTIFICATION: There are 0 Coldfront (django) project members which could be added to OpenLDAP for this project
NOTIFICATION: Both Coldfront django and OpenLDAP have 0 members - no action to take by sync_members
```

**Outcome:** all projects checked, status looks ok.



### Scenario 3 - OpenLDAP offline when project CDF0004 had title update (require description update)

- The project is checked without options - not necessary here, but to illustrate
- The project is then checked for title update by supplying ``-d``, this means that the OpenLDAP description could be updated
- Finally it is updated by also supplying sync (``-s``)


```
(coldfront_venv) [coldfront@coldfront coldfront]$ coldfront project_openldap_sync -p CDF0004
--------------------
processing Project CDF0004

search project OU result: True
search project archive OU result: False
Project CDF0004 is a new or active project - found cn=CDF0004,ou=CDF0004,ou=projects,dc=coldfront,dc=ac,dc=uk
NOTIFICATION: There are 0 Coldfront (django) project members which could be added to OpenLDAP for this project
NOTIFICATION: Both Coldfront django and OpenLDAP have 0 members - no action to take by sync_members


(coldfront_venv) [coldfront@coldfront coldfront]$ coldfront project_openldap_sync -p CDF0004 -d
--------------------
processing Project CDF0004

search project OU result: True
search project archive OU result: False
Project CDF0004 is a new or active project - found cn=CDF0004,ou=CDF0004,ou=projects,dc=coldfront,dc=ac,dc=uk
NOTIFICATION: There are 0 Coldfront (django) project members which could be added to OpenLDAP for this project
NOTIFICATION: Both Coldfront django and OpenLDAP have 0 members - no action to take by sync_members
OLD openldap_description is      INSTITUTE: CardiffUniversity | PI: ldapuser1 | TITLE: cf project 4
NEW openldap_description will be INSTITUTE: CardiffUniversity | PI: ldapuser1 | TITLE: cf project 4 - updated title
SYNC required to update OpenLDAP description


(coldfront_venv) [coldfront@coldfront coldfront]$ coldfront project_openldap_sync -p CDF0004 -d -s
Enabling writes - Syncing OpenLDAP with ColdFront
--------------------
processing Project CDF0004

search project OU result: True
search project archive OU result: False
Project CDF0004 is a new or active project - found cn=CDF0004,ou=CDF0004,ou=projects,dc=coldfront,dc=ac,dc=uk
NOTIFICATION: There are 0 Coldfront (django) project members which could be added to OpenLDAP for this project
NOTIFICATION: Both Coldfront django and OpenLDAP have 0 members - no action to take by sync_members
INSTITUTE: CardiffUniversity | PI: ldapuser1 | TITLE: cf project 4 - updated title
```
