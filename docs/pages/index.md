# What is ColdFront?

ColdFront is an open source resource and allocation management system designed to provide a
central portal for administration, reporting, and measuring scientific impact
of cyberinfrastructure resources. ColdFront was created to help high performance computing (HPC) centers manage access to a diverse set of resources across large groups of users and provide a rich set of
extensible meta data for comprehensive reporting. The flexiblity of ColdFront allows centers to manage and automate their policies and procedures within the framework provided or extend the functionality with [plugins](#extensibility).  ColdFront is written in Python and released under the AGPLv3 license.

## Features

- Allocation based system for managing access to resources
- Self-service portal for users to request access to resources for their research group
- Collection of Project, Grant, and Publication data from users
- Center director approval system and annual project review process
- Email notifications for expiring/renewing access to resources
- Ability to define custom attributes on resources and allocations 
- Integration with 3rd party systems for automation, access control, and other system provisioning tasks

## Principal investigators (PIs) or Project Owners

Principal investigators (PIs) can use ColdFront as a self-service portal to do
the following tasks:

- Request allocations to center sources such as clusters, cloud resources,
  servers, storage, and software licenses
- Add/remove user access to/from allocated resources without requiring system
  administrator interaction
- Elevate selected users to 'manager' status, allowing them to handle some of the PI tasks such as request new and renew expiring resource allocations, add/remove users to/from resource allocations, add project data such as grants and publications
- Monitor resource utilization such as storage and cloud usage
- Receive email notifications for expiring/renewing access to resources as well as notifications when allocations change status - i.e. activated, expired, denied
- Provide information such as grants, publications, and other reportable data for periodic review by center director to demonstrate need for the resources

## HPC system administrators

HPC system administrators can use ColdFront as a management portal and a command line tool to complete the following tasks:

- Approve/deny resource allocation requests
- Define when a resource allocation will expire
- Associate attributes with resources and allocations for access control automation
- Automate job scheduler account management by utilizing attributes on resources and allocations (currently supports the Slurm job scheduler)
- Manage availability of resources. Resources can be public or private. Private resources can be made available on per-user or per-group basis
- Require PIs to periodically review their projects to ensure user access is kept up to date which helps keep systems secure and data protected
- Integrate with multiple authentication options such as local database, LDAP, or OpenIdConnect (FreeIPA-based)


## Center directors

Center directors can use ColdFront to do the following:

- Measure center impact based on grants, publications, and other research output entered by PIs
- Collect return on investment metrics to position HPC center for sustainability
- Interact with PIs on project reviews ensuring they provide all required information 
- Periodically review PI access to center resources
- Explore all projects, resource allocations, grants, and publications with read only access

## Extensibility

ColdFront can easily be extended and customized to fit your center's use cases. ColdFront is written in Python using the Django web framework. The Django web framework organizes related set of features into apps. Apps are combined together to make up a project or system. ColdFront separates its apps into two
categories: core and plugins. The core apps support the core functionality of ColdFront. The plugin apps extend or modify the core functionality of ColdFront. For instance, they can integrate with third party systems for job scheduler account automation and access control.  

## Contact Us

Source code on Github: https://github.com/ubccr/coldfront

If you would like a live demo followed by QA, please contact us at
ccr-coldfront-admin-list@listserv.buffalo.edu. You can also contact us for
general inquiries and installation troubleshooting.

If you would like to join our mailing list to receive news and updates, please
send an email to listserv@listserv.buffalo.edu with no subject, and the
following command in the body of the message:

```
subscribe ccr-open-coldfront-list@listserv.buffalo.edu first_name last_name
```

## License

ColdFront is released under the AGPLv3 license
