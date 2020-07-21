# Introduction

ColdFront is an open source HPC resource allocation and management system. It
is designed as a one stop solution for three main roles in any HPC center:
principal investigator, HPC system administrator, and center director. 

## Principal investigators (PIs)

Principal investigators (PIs) can use ColdFront as a self-service portal to do
the following tasks:

- Request allocation to center sources such as clusters, cloud resources,
  servers, storage, or software licenses
- Add/remove user access to/from allocated resources without requiring system
  administrator interaction
- Elevate selected users to privileged status, allowing them to request new
  resource allocations and add/remove users to/from resource allocations on
  behalf of the PI
- Receive email notifications for expiring/renewing access to resources
- Monitor resource utilization such as storage and cloud usage
- Organize resource allocations, authorized users to PI resource allocations,
  and grants and publications generated from utilizing HPC center resources in
  projects for periodic review by center director to demonstrate need for the
  resources

## HPC system administrators

HPC system administrators can use ColdFront as a management portal and a
command line tool to do the following tasks:

- Approve/deny resource allocation requests. PI and users for whom the PI has
  requested access are notified automatically via email when a resource
  allocation request is approved. 
- Set when a resource allocation will expire
- Manage availability of resources. Resources can be public or private. Private
  resources can be made available on per-user or per-group basis. 
- Require PIs to periodically review users who can access their resource
  allocations. Any changes made is automatically applied to the resources. 
- Integrate with multiple authentications such as local database, LDAP, or
  OpenIdConnect (FreeIPA-based)
- Associate attributes with resources and allocations for access control
  automation 
- Automate job scheduler account management by utilizing attributes on
  resources and allocations

## Center directors

Center directors can use ColdFront to do the following:

- Measure center impact based on grants and publications entered by PIs
- Collect return on investment metrics to position HPC center for
  sustainability 
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
