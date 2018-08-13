# SLURM integration for Coldfront

Coldfront django extra app providing SLURM integration for Coldfront.
Subscriptions in Coldfront are marshalled out to SLURM associations in the
SLURM flat file format and can be loaded with sacctmgr. For more information on
the SLURM flat file format see [here](https://slurm.schedmd.com/sacctmgr.html).

## Design

Resources in Coldfront map to Clusters (or partitions within a cluster) in
SLURM. The name of the SLURM cluster is taken from a resource attribute in
Coldfront named "SLURM cluster name".  You can optionally provide SLURM
specifications for a cluster using a resource attribute named "SLURM
specifications". The value of this attribute must conform to the SLURM
specification format and are colon separated.

Subscriptions in Coldfront map to Accounts in SLURM. The name of the SLURM
account is taken from a subscription attribute in Coldfront named "SLURM
account name". You can optionally provide SLURM specifications for the account
using a subscription attribute named "SLURM specifications". The value of this
attribute must conform to the SLURM specification format and are colon
separated.

Subscription users in Coldfront map to Users in SLURM. It is assumed all users
inherit any SLURM specifications on the account. Adding SLURM specificatins per
user is not currently supported.

## Usage

To enable this extra app add or uncomment the following in your
local\_settings.py file:

```
    EXTRA_APPS += [
        'extra.djangoapps.slurm',
    ]
```

To generate SLURM association data from Coldfront run the following command:

```
    $ python manage.py sacctmgr_dump -o tux.cfg
```

You can then load this file into SLURM with the following command:

```
    $ sacctmgr load file=tux.cfg

```
