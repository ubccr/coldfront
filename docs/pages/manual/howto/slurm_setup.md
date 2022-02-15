# Slurm Resource Setup  

A Slurm cluster needs to be created as a resource in ColdFront.  PIs would then request allocations for that resource.  Center admins would activate the allocation and associate attributes on the allocation for the Slurm plugin to interact with.

### Step 1 - Create the Resource

In the ColdFront admin interface, navigate to Resources.  Click on the "Add Resource" button and fill out the form.  This screenshot shows an example of a Cluster resource.
![New Slurm Cluster](../../images/resources.PNG)

**Resource Type:** Cluster  
**Parent Resource:** leave blank  
**Is allocatable:** check  
**Name:** name of your cluster   
NOTE: this name will show up in the drop down list for PIs.  It can be multiple words and does not need to be the name of the slurm cluster.  We'll enter that as an attribute.    
**Description:** a description of the resource  
**Is available:** check  
**Is public:** check   
**Allowed groups and allowed users:**  You can add these restrictions if you want to make the resource available only to a selection of users/groups  


Under "Resource Attributes" click "Add another resource attribute"  
Select slurm cluster from the attribute menu and enter the name of your Slurm cluster (found in slurm_cluster.conf)  
Select slurm_specs from the attribute menu and enter any slurm specs necessary for your cluster.  These are found in the slurm_cluster.conf file as well and include default values and other options you want inherited for all accounts on that cluster.  See the screenshot below as an example.  The slurm_specs and slurm_user_specs attributes can also be added to allocations for the resource.  When on the allocation, they apply to only the slurm account on that allocation, not the whole cluster.

**Click the 'SAVE' button!**

![Slurm Attributes](../../images/slurm_cluster.PNG)

### Step 2 - Create an Allocation for the Resources

Login as the PI and request an allocation for the new resource.  
- Under the PI's project, click 'Request Resource Allocation'  
- Select the cluster resource off the drop down list and enter a justification.  This is usually used by centers to get PIs to say why they need access to a particular resource.  
- Select any other project users to add to the allocation.  
- Click the Submit button.  

![Slurm Attributes](../../images/request_alloc.PNG)

A new allocation is created with a status of 'New'  No access is provided to the user until the allocation is activated.

### Step 3 - Activate the allocation

When logged in as a center admin, navigate to the Admin menu and click on 'Allocation Requests'  

![Slurm Attributes](../../images/admin_approve.PNG)

From here, the admin has a few options:  
- You can click on the project title and you'll be redirected to the Project Detail page  
- You can click on the allocation ID number and you'll be redirected to the Allocation Detail page  
- You can click on the "Deny" button and the allocation status will change to 'denied.'  The PI and allocation users will get an email notifying them that the allocation has been denied.  
- If you click on the "Approve" button, the allocation status will update to 'active' and the expiration date will be set one year out.  

Most of the time, we want to set allocation attributes on the allocation before approving it, so that the plugins can interact and accounts get updated.  In this example, we want to set some Slurm attributes on the allocation before activating it.  Click on the allocation ID number to go to the Allocation detail page:  

![Slurm Attributes](../../images/alloc_setup.PNG)

Here we add 3 slurm attributes to the allocation:
- slurm_account_name = PIusername (this will depend on how you name your slurm accounts - PI name, project name/ID, etc)
- slurm_specs = Fairshare=100 (this is the fairshare applied to the slurm account)
- slurm_user_specs = Fairshare=parent (this is the fairshare value inherited by all the associations of the slurm account)

We also change the status of the allocation to 'Active' and set today's date and the end date of the allocation.  If your allocation is good for one year, you could also go back to the "Allocation Requests" page and click the "Approve" button to set this all automatically.


### Step 4 - Sync with Slurm  

Your [ColdFront config](../../config.md) must have the [Slurm plugin](https://github.com/ubccr/coldfront/tree/master/coldfront/plugins/slurm) enabled and you'll need the Slurm client installed on your ColdFront instance so it can run the slurm commands.  

Within your ColdFront virtual environment, dump the Slurm account and association from ColdFront:  

```
-c = cluster name  
-o = output location  

coldfront slurm_dump -c hpc -o ~/slurm_dump
cat ~/slurm_dump/hpc.cfg
# ColdFront Allocation Slurm associations dump 2021-04-01
Cluster - 'hpc':DefaultQOS='compute':Fairshare=1:QOS+=compute,viz,debug,scavenger
Parent - 'root'
User - 'root':DefaultAccount='root':AdminLevel='Administrator':Fairshare=1
Account - 'cgray':Fairshare=100
Parent - 'cgray'
User - 'cgray':Fairshare=parent
User - 'sfoster':Fairshare=parent
```

This command outputs the slurm information from all ACTIVE allocations for cluster resources.  

Now load the dump into the slurm database - this slurm command does a diff between what is currently in the database and ADDS anything new it finds in this file.  It does NOT remove anything.  You'll see a listing of the changes it intends to make and have the option to accept them or cancel out.

```
sacctmgr load file=~/slurm_dump/hpc.cfg
For cluster hpc
Accounts
      Name                Descr                  Org                  QOS
---------- -------------------- -------------------- --------------------
     cgray                cgray                cgray
---------------------------------------------------

Account Associations
   Account   Par Name     Share   GrpTRESMins GrpTRESRunMin       GrpTRES GrpJobs GrpJobsAccrue  GrpMem GrpNodes GrpSubmit     GrpWall   MaxTRESMins       MaxTRES MaxTRESPerNode MaxJobs MaxSubmit MaxNodes     MaxWall                  QOS   Def QOS
---------- ---------- --------- ------------- ------------- ------------- ------- ------------- ------- -------- --------- ----------- ------------- ------------- -------------- ------- --------- -------- ----------- -------------------- ---------
     cgray       root       100                                                                                                     
--------------------------------------------------------------

Users
      Name   Def Acct  Def WCKey                  QOS     Admin       Coord Accounts
---------- ---------- ---------- -------------------- --------- --------------------
     cgray      cgray                                   Not Set
---------------------------------------------------

User Associations
      User    Account     Share   GrpTRESMins GrpTRESRunMin       GrpTRES GrpJobs GrpJobsAccrue  GrpMem GrpNodes GrpSubmit     GrpWall   MaxTRESMins       MaxTRES MaxTRESPerNode MaxJobs MaxSubmit MaxNodes     MaxWall                  QOS   Def QOS
---------- ---------- --------- ------------- ------------- ------------- ------- ------------- ------- -------- --------- ----------- ------------- ------------- -------------- ------- --------- -------- ----------- -------------------- ---------
     cgray      cgray    parent                                                                                                     
   sfoster      cgray    parent                                                                                                     
--------------------------------------------------------------

sacctmgr: Done adding cluster in usec=440457
Would you like to commit changes? (You have 30 seconds to decide)
(N/y): y

```

That's it!  This can be cron'd to run on a regular basis or run manually so staff can ensure accuracy.


### Removing access for expired or revoked allocations

When an allocation for a slurm resource expires or is revoked, we want to remove the slurm account and associations on that allocation.  To do that, run the slurm_check process:

```
coldfront slurm_check -h
usage: coldfront slurm_check [-h] [-i INPUT] [-c CLUSTER] [-s] [-n]
                             [-u USERNAME] [-a ACCOUNT] [-x] [--version]
                             [-v {0,1,2,3}] [--settings SETTINGS]
                             [--pythonpath PYTHONPATH] [--traceback]
                             [--no-color] [--force-color]

Check consistency between Slurm associations and ColdFront allocations

optional arguments:
  -h, --help            show this help message and exit
  -i INPUT, --input INPUT
                        Path to sacctmgr dump flat file as input. Defaults to
                        stdin
  -c CLUSTER, --cluster CLUSTER
                        Run sacctmgr dump [cluster] as input
  -s, --sync            Remove associations in Slurm that no longer exist in
                        ColdFront
  -n, --noop            Print commands only. Do not run any commands.
  -u USERNAME, --username USERNAME
                        Check specific username
  -a ACCOUNT, --account ACCOUNT
                        Check specific account
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

You can run it and check by slurm account name or provide a slurm flat file. If you run in --noop mode, you'll be provided with a list of the changes to review.  If you run in --sync mode the changes will be made without intervention.  In the example above, if we expire the cgray allocation and then run this slurm_check tool, we see:

```
coldfront slurm_check --noop -c hpc -a cgray
NOOP enabled
cgray   cgray   hpc     Remove
sfoster cgray   hpc     Remove
        cgray   hpc     Remove
```
If we run without specifying the account, we may see additional accounts and associations that need to be removed:

```
coldfront slurm_check --noop -c hpc
NOOP enabled
cgray   cgray   hpc     Remove
sfoster cgray   hpc     Remove
        cgray   hpc     Remove
astewart        sfoster hpc     Remove
sfoster sfoster hpc     Remove
        sfoster hpc     Remove
hpcadmin        staff   hpc     Remove
        staff   hpc     Remove
```
This can be cron'd like the slurm_dump process or run manually.

### Alternate Step 4 - Finer-grained Synchronization with Slurm  

If you prefer more control over the process of synchronizing ColdFront with Slurm than is provided with the "slurm\_dump" and "slurm\_check" commands, the "slurm\_sync" command is also provided.  The "slurm\_sync" command will compare the cluster/account/user structure in Slurm (via a providedSlurm flat file dump) to what ColdFront thinks the Slurm configuration should be, and issue the appropriate Slurm sacctmgr commands to make the Slurm configuration agree with ColdFront.

There is a "noop" flag available so that you can see the actual sacctmgr commands which would be run (either as a check before allowing the slurm\_sync command from running them, or to save to a file and edit).  The slurm\_sync command also accepts a number of flags to control its before.  A full list of available flags can be seen by giving it the "--help-flags" option.  Flags are strings that can be passed to the slurm\_sync command
using the -f or --flags option; you can pass multiple flags by repeated use of the option.  Recognized flags are:

- _skip\_create\_cluster_: If this flag is given, slurm\_sync will not create a cluster if missing in the Slurm flat file dump.  (*Note*: accounts and users in the missing cluster will not be created either).

- _skip\_delete\_cluster_: If this flag is given, slurm\_sync will not delete a cluster if missing in ColdFront. (*Note*: accounts and users underneath the missing cluster will not be deleted either.).  Note that even without this flag, slurm\_sync will *not* issue commands to delete a cluster unless the _force\_delete\_cluster_ flag is also given, for safety.

- _force\_delete\_cluster_: For safety reasons, slurm\_sync will *not* normally delete a cluster even if it is missing in ColdFront, but instead give a warning and force "noop" mode. Only if this flag is given will slurm\_sync actually execute the commands to delete a cluster if the cluster is missing in ColdFront.

- _skip\_cluster\_specs_: If this flag is given, slurm\_sync will disregard the cluster specs when comparing clusters in Slurm and ColdFront.  I.e., even if the cluster specs differ, it will not issue a command to bring the Slurm cluster into agreement with ColdFront.

- _skip\_create\_account_: If this flag is given, slurm\_sync will not create an account missing in the Slurm flat file dump.  *Note*: this also suppresses the creation of users underneath the missing account.

- _skip\_delete\_account_: If this flag is given, slurm\_sync will not issue commands to delete an account present in Slurm but not in ColdFront.  *Note*: this also suppresses the deletion of users underneath the missing account.  *Note*: if the cluster containing the account is being deleted, this will not prevent the deletion of the account.

- _skip\_account\_specs_: If this flag is given, slurm\_sync will disregard the account specs when comparing accounts in Slurm and ColdFront.  I.e., even if the account specs differ, it will not issue a command to bring the Slurm account into agreement with ColdFront.

- _skip\_create\_user_: If this flag is given, slurm\_sync will not create users missing in the Slurm flat file dump.

- _skip\_delete\_user_: If this flag is given, slurm\_sync will not delete users in the Slurm flat file dump but not in ColdFront.  *Note*: if the allocation containing the user is being deleted, this will not prevent the deletion of the user.

- _skip\_user\_specs_: If this flag is given, slurm\_sync will disregard the user specs when comparing users in Slurm and ColdFront.  I.e., even if the user specs differ, it will not issue a command to bring the Slurm user into agreement with ColdFront.

- _ignore\__***SPECFIELD***: If this flag is given, the Slurm spec ***SPECFIELD*** will be ignored when comparing specs (at any level).  Other specs for the object will still be considered.  *Note*: this only affects situations in which slurm\_sync would issue a modification command; if slurm\_sync wants to create the object, it will still give the full spec string.

- _ignore\_-***SPECFIELD***_***SUBFIELD***: This flag is similar to the above, but instructs slurm\_sync to ignore a single component ***SUBFIELD*** in a TRES-like spec ***SPECFIELD***.  Other components of ***SPECFIELD*** will still be considered.

*NOTE*: The slurm\_sync command tries to handle set-like specs (e.g. QoS and other specs which can use the += notation), but that has not been fully tested.  
