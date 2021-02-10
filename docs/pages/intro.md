# Introduction

ColdFront is an open source HPC resource allocation management system. It
is designed as a one stop solution for three main roles in any HPC center:
principal investigator, HPC system administrator, and center director.

## Principal investigators (PIs) or Project Owners

Principal investigators (PIs) can use ColdFront as a self-service portal to do
the following tasks:

- Request allocations to center sources such as clusters, cloud resources,
  servers, storage, and software licenses
- Add/remove user access to/from allocated resources without requiring system
  administrator interaction
- Elevate selected users to 'manager' status, allowing them to handle some of the PI tasks such as request new resource allocations, add/remove users to/from resource allocations, add project data like grants and publications
- Monitor resource utilization such as storage and cloud usage
- Receive email notifications for expiring/renewing access to resources as well as notifications when allocations change status - i.e. activated, expired, denied
- Provide information such as grants, publications, and other reportable data
  for periodic review by center director to demonstrate need for the
  resources

## HPC system administrators

HPC system administrators can use ColdFront as a management portal and a
command line tool to complete the following tasks:

- Approve/deny resource allocation requests.
- Define when a resource allocation will expire
- Associate attributes with resources and allocations for access control
  automation
- Automate job scheduler account management by utilizing attributes on
  resources and allocations (currently supports the Slurm job scheduler)
- Manage availability of resources. Resources can be public or private. Private
  resources can be made available on per-user or per-group basis.
- Require PIs to periodically review their projects to ensure user access is kept up to date which helps keep systems secure and data protected.
- Integrate with multiple authentication options such as local database, LDAP, or
  OpenIdConnect (FreeIPA-based)


## Center directors

Center directors can use ColdFront to do the following:

- Measure center impact based on grants, publications, and other research output entered by PIs
- Collect return on investment metrics to position HPC center for
  sustainability
- Interact with PIs on project reviews ensuring they provide all required information (these reviews can be configured for frequency or turned off completely)
- Periodically review PI access to center resources
- Explore all projects, resource allocations, grants, and publications with
  read only access


ColdFront is written in Python using the Django web framework. The Django web
framework organizes related set of features into apps. Apps are combined
together to make up a project or system. ColdFront separates its apps into two
categories: core and plugins. The core apps support the core functionality of
ColdFront. The plugin apps extend or modify the core functionality of
ColdFront. For instance, they can integrate with third party systems for job
scheduler account automation and access control.  
