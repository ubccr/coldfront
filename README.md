# myBRC User Portal

[![Documentation Status](https://readthedocs.org/projects/coldfront/badge/?version=latest)](https://coldfront.readthedocs.io/en/latest/?badge=latest)

The myBRC User Portal is an access management system for Berkeley Research
Computing. It enables users to create or join projects, gain access to the
clusters managed by BRC, view the statuses of their requests and access, view
their allocation quotas and usages, and update personal information. It enables
administrators to handle these requests and manage users and projects. The
portal is built on top of ColdFront.

ColdFront is an open source resource allocation system designed to provide a
central portal for administration, reporting, and measuring scientific impact
of HPC resources. ColdFront was created to help HPC centers manage access to a
diverse set of resources across large groups of users and provide a rich set of
extensible meta data for comprehensive reporting. ColdFront is written in
Python and released under the GPLv3 license.

## Quick Install

1. ColdFront requires Python 3.6, memcached, and redis. 

### CentOS (7)

Install EPEL then install required packages:

```
sudo yum install epel-release
sudo yum install python36 python36-devel memcached redis

# Install SQLite >= 3.8.3 from source since it is absent from the CentOS software repositories
wget https://sqlite.org/2020/sqlite-autoconf-XXXXXXX.tar.gz
tar -xzf sqlite-autoconf-XXXXXXX
cd sqlite-autoconf-XXXXXXX
./configure
make
make install

#Check version
sqlite3 --version
``` 


### CentOS (8)

Install EPEL then install required packages:

```
sudo yum install epel-release
sudo yum install python36 python36-devel memcached redis
``` 

### Ubuntu (16.04)
```
sudo add-apt-repository ppa:jonathonf/python-3.6
sudo apt-get update
sudo apt-get install python3.6 python3.6-venv memcached redis-server
``` 

2. Clone ColdFront in a new directory and create a Python virtual environment for ColdFront
```
mkdir coldfront_app
cd coldfront_app
git clone https://github.com/ubccr/coldfront.git
python3.6 -mvenv venv
```

3. Activate the virtual environment and install the required Python packages
```
source venv/bin/activate
cd coldfront
pip install wheel
pip install -r requirements.txt

```

4. Copy coldfront/config/local_settings.py.sample to coldfront/config/local_settings.py. 
```
cp coldfront/config/local_settings.py.sample coldfront/config/local_settings.py
```

5. Copy config/local_strings.py.sample to config/local_strings.py and update if desired. 
```
cp coldfront/config/local_strings.py.sample coldfront/config/local_strings.py
```

6. Run initial setup
```
python manage.py initial_setup
```

7. OPTIONAL: Add some test data
```
python manage.py load_test_data
```

8. Start development server
```
python manage.py runserver 0.0.0.0:8000
```

9. Point your browser to http://localhost:8000

You can log in as `admin` with password `test1234`. 
You can log in as a PI using username `cgray` with password `test1234`.
You can log in as another PI using username `sfoster` with password `test1234`.

Password for all users is also `test1234`.

### Additional myBRC Setup Steps

10. Run a command to create database objects needed for accounting.

```
python manage.py add_brc_accounting_defaults
```

## Directory structure

- coldfront
    - core - The core ColdFront application
        - field_of_science
        - grant
        - portal
        - project
        - publication
        - resource
        - statistics
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

## Accessibility

The service should be accessible to people with disabilities.

In practice, when contributing to the code, ensure that changes do not cause
accessibility issues to be flagged by the
[tota11y](https://khan.github.io/tota11y/) tool. This will be considered
during the code review process.

## Deployments

Deployments and configuration management are handled by Ansible, located in
the `bootstrap/ansible` directory.

In particular, the Ansible playbook installs, enables, and configures
PostgreSQL, creates log files, installs Pip requirements, copies ColdFront
settings files, runs initial setup, migrates the database, collects static
files, creates WSGI files for Apache, and restarts Apache.

Note that there are some additional server setup steps that are not currently
captured in the Ansible playbook.

1. Create `main.yml`.

```
cp bootstrap/ansible/main.copyme main.yml
```

2. Modify `main.yml` depending on the current deployment.

3. Run the Ansible playbook as the `djangooperator` user defined in `main.yml`.

```
ansible-playbook bootstrap/ansible/setup_cf_mybrc.yml
```

## License

ColdFront is released under the GPLv3 license. See the LICENSE file.
