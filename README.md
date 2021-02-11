# ColdFront - Resource Allocation System

[![Documentation Status](https://readthedocs.org/projects/coldfront/badge/?version=latest)](https://coldfront.readthedocs.io/en/latest/?badge=latest)

ColdFront is an open source resource allocation system designed to provide a
central portal for administration, reporting, and measuring scientific impact
of HPC resources. ColdFront was created to help HPC centers manage access to a
diverse set of resources across large groups of users and provide a rich set of
extensible meta data for comprehensive reporting. ColdFront is written in
Python and released under the GPLv3 license.

## Features

- Allocation based system for managing access to resources
- Collect Project, Grant, and Publication data from users
- Define custom attributes on resources and allocations
- Email notifications for expiring/renewing access to resources
- Integration with 3rd party systems for automation and access control
- Center director approval system and annual project reviews

## Plug-in Documentation
 - [Slurm](coldfront/plugins/slurm)
 - [FreeIPA](coldfront/plugins/freeipa)
 - [LDAP](coldfront/plugins/ldap_user_search)
 - [Mokey/Hydra OpenID Connect](coldfront/plugins/mokey_oidc)
 - [iQuota](coldfront/plugins/iquota)
 - [Open OnDemand](coldfront/plugins/ondemand)
 - [Open XDMoD](coldfront/plugins/xdmod)
 - [System Monitor](coldfront/plugins/system_monitor) (example of ways to integrate your own plug-ins)


## Installation

[Quick Start Instructions](docs/pages/quickstart.md)


## Directory structure

- coldfront
    - core - The core ColdFront application
        - field_of_science
        - grant
        - portal
        - project
        - publication
        - resource
        - allocation
        - user
        - utils
    - libs - Helper libraries
    - plugins - Plugins that can be configured in ColdFront
        - freeipa
        - iquota
        - ldap_user_search
        - mokey_oidc
        - slurm
        - system_monitor



## ColdFront Demos

[Animated gifs demonstrating ColdFront features](docs/pages/demos.md)



## Contact Information
If you would like a live demo followed by QA, please contact us at ccr-coldfront-admin-list@listserv.buffalo.edu. You can also contact us for general inquiries and installation troubleshooting.

If you would like to join our mailing list to receive news and updates, please send an email to listserv@listserv.buffalo.edu with no subject, and the following command in the body of the message:

subscribe ccr-open-coldfront-list@listserv.buffalo.edu first_name last_name


## License

ColdFront is released under the GPLv3 license. See the LICENSE file.
