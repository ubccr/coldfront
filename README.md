# Coldfront - Resource Allocation System

Coldfront is an open source resource allocation system designed to provide a
central portal for administration, reporting, and measuring scientific impact
of HPC resources. Coldfront was created to help HPC centers manage access to a
diverse set of resources across large groups of users and provide a rich set of
extensible meta data for comprehensive reporting. Coldfront is written in
Python and released under the GPLv3 license.

## Features

- Allocation/Subscription based system for managing access to resources
- Collect Project, Grant, and Publication data from users
- Define custom attributes on resources and subscriptions
- Email notifications for expiring/renewing access to resources
- Integration with 3rd party systems for automation and access control
- Center director approval system and annual project reviews


## Quick Install
1. Coldfront requires Python 3.6, memcached, and redis. 

### CentOS (7.5)

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

2. Clone Coldfront in a new directory and create a Python virtual environment for Coldfront
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

4. Copy config/local_settings.py.sample to config/local_settings.py. 
```
cp config/local_settings.py.sample config/local_settings.py
```
Open config/local_settings.py and update the following:
* Update `SECRET_KEY`. Consider making the length at least 50 characters long. 
* Update `TIME_ZONE` if necessary


5. Copy config/local_strings.py.sample to config/local_strings.py and update if desired. 
```
cp config/local_strings.py.sample config/local_strings.py
```

6. Run initial setup
```
python manage.py initial_setup
```

7. Setup an admin user
```
python manage.py createsuperuser
```

8. Optional: Add some dummy data
```
python manage.py load_dummy_data
```

9. Start development server
```
python manage.py runserver 0.0.0.0:8000
```

10. Point your browser to http://localhost:8000

You can log in as `admin` with password `test1234`. 
You can log in as a PI using username `ccollins` with password `test1234`.
You can log in as director role using username `michardson` with password `test1234`.



## Directory structure

- core - The core Coldfront application
- common - Common code shared between applications
- extra - Extra applications that can be configured in Coldfront

## License

Coldfront is released under the GPLv3 license. See the LICENSE file.
