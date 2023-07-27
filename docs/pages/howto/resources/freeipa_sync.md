# FreeIPA Account Syncing

The [FreeIPA plugin](https://github.com/ubccr/coldfront/tree/master/coldfront/plugins/freeipa) for ColdFront allows for the syncing of unix group membership between ColdFront allocations and FreeIPA.

```
coldfront freeipa_check --help
usage: coldfront freeipa_check [-h] [-s] [-u USERNAME] [-g GROUP] [-n] [-x]
                               [--version] [-v {0,1,2,3}]
                               [--settings SETTINGS] [--pythonpath PYTHONPATH]
                               [--traceback] [--no-color] [--force-color]

Sync groups in FreeIPA

optional arguments:
  -h, --help            show this help message and exit
  -s, --sync            Sync changes to/from FreeIPA
  -u USERNAME, --username USERNAME
                        Check specific username
  -g GROUP, --group GROUP
                        Check specific group
  -n, --noop            Print commands only. Do not run any commands.
  -x, --header          Include header in output
  --version             show program's version number and exit
  -v {0,1,2,3}, --verbosity {0,1,2,3}
                        Verbosity level; 0=minimal output, 1=normal output,
                        2=verbose output, 3=very verbose output
  --settings SETTINGS   The Python path to a settings module, e.g.
                        "myproject.settings.main". If this isn't provided, the
                        DJANGO_SETTINGS_MODULE environment variable will be
                        used.
  --pythonpath PYTHONPATH
                        A directory to add to the Python path, e.g.
                        "/home/djangoprojects/myproject".
  --traceback           Raise on CommandError exceptions
  --no-color            Don't colorize the command output.
  --force-color         Force colorization of the command output.
```

Running the freeipa_check tool will compare all user accounts with all active allocations that have at least one freeipa_group attribute.  This tool can be run on a single user or group or against the whole ColdFront user database.  The tool will display what changes need to be made, either adding or removing the user(s) from the group(s), as shown here.  

```
coldfront freeipa_check -n -x -u ccrgst72
ipa: WARNING: NOOP enabled
username        add_missing_freeipa_group_membership    remove_existing_freeipa_group_membership        freeipa_status  coldfront_status
ipa: WARNING: User ccrgst72 should be added to freeipa group: testgroup
ccrgst72        testgroup               Enabled Active
```

To make the changes, remove the noop mode (-n) and add the sync mode (-s).  This can be setup in a cron to run periodically and make the updates automatically.  This will ensure access to resources based on unix group are removed when allocations expire or are revoked.
