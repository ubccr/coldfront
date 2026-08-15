---
icon: lucide/download
---

# Install ColdFront

This section describes how to install ColdFront. New releases of ColdFront
can introduce breaking changes. Refer to the [upgrade guide](upgrading.md) for
more information.

## Requirements

ColdFront requires Python 3.12 or a later version.

## Download ColdFront

You can download ColdFront releases from:

- [PyPI](https://pypi.org/project/coldfront/#files)
- [GitHub](https://github.com/coldfront/coldfront/releases)

## Install ColdFront

### Install with uv (recommended)

The recommended way to install ColdFront is with [uv](https://docs.astral.sh/uv/):

```
$ uv tool install coldfront
```

### Install with pip

You can install ColdFront with pip inside a virtual environment:

```
$ python3 -m venv venv
$ source venv/bin/activate
$ pip install --upgrade pip
$ pip install coldfront
```

### Install from source

If you want to work on the ColdFront source code, clone the repository and
install the dependencies:

```
$ git clone https://github.com/coldfront/coldfront.git
$ cd coldfront
$ uv sync
```

!!! tip "Use a tagged release"

    The main branch has the latest changes and can be unstable. To use a
    tagged release, run:

    ```
    $ git tag -l
    $ git checkout v2.0.0
    ```

## Configure the Database

ColdFront supports SQLite, MariaDB, MySQL, and PostgreSQL. By default,
ColdFront uses SQLite and creates a database file in your current working
directory.

Refer to the [configuration guide](../configuration/index.md) for more information about
database settings.

## Initialize the Database

After you configure the database, initialize the ColdFront database. Do this
only one time:

```
$ uv run coldfront migrate
```

## Create a Super User

Create a super user account to access the administration interface:

```
$ uv run coldfront createsuperuser
```

This command asks you to select a user name, a password, and an email
address for the super user account.

## Run the Development Server

ColdFront is a Django application. It comes with a simple web server for
testing and evaluation purposes. To start the development server:

```
$ DEBUG=True uv run coldfront runserver
```

Open your browser to http://localhost:8000 and log in with the super user
account you created.

!!! danger "Do not run the development server in production"

    The development server is not safe for production use. For information
    about deploying ColdFront in production, see the [deployment guide](deploy.md).

## Load Test Data

If you want to evaluate ColdFront, you can load a test data set:

```
$ DEBUG=True PLUGINS="coldfront_initializer" uv run coldfront load_test_data
```

After you load the test data, you can log in with these accounts:

- Administrator: user name `admin`, password `test1234`
- Principal investigator: user name `cgray`, password `test1234`
- Center director: user name `csimmons`, password `test1234`

!!! danger "Do not use test data in production"

    The test data creates user accounts with weak passwords. These accounts
    are safe only for testing purposes. If you load test data, delete the
    user accounts before you deploy in production.
