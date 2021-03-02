# Installation

This section describes the various methods of installing ColdFront. New
releases of ColdFront may introduce breaking changes. Please refer to the
[upgrading section](upgrading.md) and changelog for more information.

## Downloading

ColdFront releases can be downloaded from
[PyPI](https://pypi.org/project/coldfront/#files) or on GitHub
[here](https://github.com/ubccr/coldfront/releases).

## Requirements

ColdFront requires Python 3.6.

## Installation Methods

### Install via pip (recommended)

The recommended way of installing ColdFront is via pip inside a virtual
environment:

```
$ python3 -mvenv venv
$ source venv/bin/activate
$ pip install --upgrade pip
$ pip install coldfront
```

### Install via source distribution

We recommend installing via pip, but if you prefer to install via a source
distribution you can download ColdFront releases via
[PyPI](https://pypi.org/project/coldfront/#files) or
[GitHub](https://github.com/ubccr/coldfront/releases). We also recommend
installing this in a virtual environment.

```
$ tar xvzf coldfront-x.x.x.tar.gz
$ cd coldfront-x.x.x
$ pip install .
```

### Developing ColdFront

If you're interested in hacking on the ColdFront source code you install by
cloning our GitHub repo and install via pip development mode. Note the master
branch is the bleeding edge version and may be unstable. You can also checkout
one of the tagged releases.
```
$ python3 -mvenv venv
$ source venv/bin/activate
$ pip install --upgrade pip
$ git clone https://github.com/ubccr/coldfront.git
$ cd coldfront
$ pip install -e .
```

!!! info "Recommended"
    Checkout a tagged release by running:
    ```
    git tag -l
    git checkout v1.x.x
    ```

## Configuring ColdFront

For complete documentation on configuring ColdFront [see here](config.md).
ColdFront can be configured via environment variables, an environment file, or
a python file which can be used for more advanced configuration settings.
ColdFront requires a database and if you don't configure one it will use SQLite
by default.

## Intializing the ColdFront database

ColdFront supports MariaDB/MySQL, PostgreSQL, and SQLite. See the complete
guide on [configuring ColdFront](config.md) for more details. By default, ColdFront will use
SQLite and create a database file in your current working directory.

After configuring your database of choice you must first initialize the
ColdFront database. This should only be done once:

```
$ coldfront initial_setup
Running migrations:
  Applying contenttypes.0001_initial... OK
  Applying auth.0001_initial... OK
  ....
  ....
```

After the above command completes the ColdFront database is ready for use. 

## Creating the super user account

Run the command below to create a new super user account:

```
$ coldfront createsuperuser
```

## Running ColdFront server

ColdFront is a Django application and comes with a simple web server to get
started quickly. This is good for evaluating ColdFront and testing/demo
purposes. Run the following command to start the development web server:

```
$ DEBUG=True coldfront runserver
```

Point your browser to http://localhost:8000 and login with the super user
account you created.

!!! danger "Danger"
    Do not run this in production. For more information on deploying ColdFront
    in production [see here](deploy.md).

## Loading the sample test data

If you're interested in evaluating ColdFront we provide an easy way to load
some test data so you can get a feel for how ColdFront works. Run this command
to load the test data set:

```
$ coldfront load_test_data
```

- You can log in as `admin` with password `test1234`.
- You can log in as a PI using username `ccollins` with password `test1234`.
- You can log in as center director using username `michardson` with password `test1234`.
- Password for all users is also `test1234`.

!!! danger "Danger"
    Do not run with this data loaded in production environment. The default
    user accounts are created with weak passwords and should only be used for
    testing purposes. If you do decide to use the test data, delete the user
    accounts created at minimum.
