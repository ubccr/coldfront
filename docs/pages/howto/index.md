# Using ColdFront  

ColdFront was designed to be flexible enough to adapt to your center's workflows and policies so there are many ways you can use it.  Here we provide a few examples of the most popular features:  

- [Annual Project Reviews for PIs](projects/project_review_PI.md)  
- [Annual Project Review Workflow for Center Staff](projects/project_review_staff.md)  
- [FreeIPA Account Syncing](resources/freeipa_sync.md)  
- [Slurm Resource Setup](resources/slurm_setup.md)  
- [Animated demos](demos.md) of ColdFront tasks such as working with projects (adding users to a project, requesting an allocation, adding grants & publications), managing allocations as an admin, and adding a resource  

## HPC Toolset Tutorial  

The [HPC Toolset Tutorial](https://github.com/ubccr/hpc-toolset-tutorial) is a collaboration with the XDMoD team at the University at Buffalo and the OnDemand team at Ohio Supercomputer Center.  It was designed to demonstrate how the three products can be used together to support the management, usage, and monitoring of HPC resources.  The toolset consists of a set of docker containers that simulate a standard HPC infrastructure - including a Slurm cluster, login node, single sign-on solution, ColdFront, XDMoD, and OnDemand.  We recommend testing ColdFront using the toolset tutorial to get a sense of how it can be used at your center.

This [presentation](https://youtu.be/9Nf1GucaVc0) provides an overview of the HPC Toolset Tutorial geared at system administrators.

## Troubleshooting  

There are a couple places you can check for information if you're having issues with ColdFront.  

Gunicorn is a Python WSGI (web server gateway interface) HTTP server that's used in Django to serve the ColdFront website.  Make sure this service is running correctly.  [See here](../deploy.md#startenable-coldfront-gunicorn-workers)  

Email issues:  If email notifications are not being sent, check to make sure the QCluster service is running.  Fix any errors and restart the service.  [See here](../deploy.md#startenable-coldfront-qcluster)  

Anything else is most likely system related and not an issue with ColdFront.  We recommend the [Django documentation](https://docs.djangoproject.com/) for details on framework ColdFront is built on.

