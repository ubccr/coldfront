Reference testing log (from development of plugin).

Detailed are tests performed and comments on testing conditions.

| Tests | Disconnect slapd required? | Comment |
| --- | --- | --- |
| **GENERAL** | | |
| add project | N | |
| add members | N | |
| remove members | N | |
| update title | N | |
| archive project - to archive ou | N |
| archive project - delete | N |
| no institution match - description correct | N | feature var was set to create DB column, then unset |
| no institution feature - description correct | N | before building environment: remove migration file, comment line in model, comment env var -> no DB column |
| no project code match - logs error | N | feature var was set to create DB column, then unset |
| no project code feature - logs error | N | before building environment: remove migration file, comment line in model, comment env var -> no DB column |
| truncate very long project title - description handled correctly | N | |
| **SYNCER MEMBERS** | | |
| wrong membership in openldap (less) | N | remove user with ldif, sync |
| wrong membership in openldap (more) | Y | stop slapd, remove user in WebUI, start slapd, sync |
| **SYNCER PROJECTS** | | |
| project missing in Openldap | Y | |
| project not archived in Openldap (not in OpenLDAP at all) | Y | |
| project in Openldap but not archived | Y | |
| updated title after slapd diconnect | Y | |
| update archived project members - add | N | remove user with ldif, sync |
| update archived project members - remove | N | add user with ldif, sync |
| project removal (not archival) | N | disabled archive ou var |
| **SYNCER MISC** | |
| project archive ou set then not set - notification | N  | var set, projects were archived, then unset, syncer notifies, but no changes in OpenLDAP |
