# Quickstart

Installing ColdFront is easy.

## Install required software

ColdFront requires Python 3.6, memcached, and redis. 

For CentOS:

```
$ sudo yum install epel-release
$ sudo yum install python36 python36-devel memcached redis
```


For Ubuntu

```
$ sudo apt-get update
$ sudo apt-get install python3.6 python3.6-venv memcached redis-server
```

## Clone from github

Clone ColdFront in a new directory:

``` 
$ mkdir coldfront_app
$ cd coldfront_app
$ git clone https://github.com/ubccr/coldfront.git
```


## Setup virtual environment and install

```
$ python3.6 -mvenv venv
$ source venv/bin/activate
$ cd coldfront
$ pip install wheel
$ pip install -e . 
```

## Configure ColdFront

Copy config/local_settings.py.sample to config/local_settings.py:

    
```
$ cp coldfront/config/local_settings.py.sample coldfront/config/local_settings.py
```

Open config/local_settings.py and update the following:
    
```
Update `SECRET_KEY`. Consider making the length at least 50 characters long. 
Update `TIME_ZONE` if necessary
```

Copy config/local_strings.py.sample to config/local_strings.py and update if desired. 
    
```
$ cp coldfront/config/local_strings.py.sample coldfront/config/local_strings.py
```

## Run initial setup
    
This will create the necessary tables in the ColdFront database. 

```
$ coldfront initial_setup
```

!!! tip "Optional"
    Load in some test data for testing out ColdFront features by running
    `coldfront load_test_data`


## Start development server

```
$ coldfront runserver 0.0.0.0:8000
```

Point your browser to http://localhost:8000

- You can log in as `admin` with password `test1234`. 
- You can log in as a PI using username `ccollins` with password `test1234`.
- You can log in as center director using username `michardson` with password `test1234`.
- Password for all users is also `test1234`. 
