# MyBRC/MyLRC User Portal

The MyBRC User Portal is an access management system for UC Berkeley Research IT's Berkeley Research Computing program. It enables users to create or join projects, gain access to the clusters managed by BRC, view the statuses of their requests and access, view their allocation quotas and usages, and update personal information. It enable administrators to handle these requests and manage users and projects.

The MyLRC User Portal is a second instance of the same system, developed for Lawrence Berkeley National Laboratory's Laboratory Research Computing program.

The portal is implemented on top of a fork of [ColdFront](https://coldfront.readthedocs.io/en/latest/).

## Getting started

1. After cloning the repository, prevent Git from detecting changes to file permissions.

   ```bash
   git config core.fileMode false
   ```

2. Select one of the following options for setting up a development environment.

   - [Docker](bootstrap/development/docker/README.md) (Recommended)
   - [Vagrant VM on VirtualBox](bootstrap/development/docs/vagrant-vm-README.md)

## Documentation

Documentation resides in a separate repository. Please request access.

### Miscellaneous Topics

- [Deployment](bootstrap/ansible/README.md)
- [REST API](coldfront/api/README.md)

## License

ColdFront is released under the GPLv3 license. See the LICENSE file.
