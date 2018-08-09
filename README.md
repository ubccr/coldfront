# Coldfront - Resource Allocation System

TODO: Write me

## Directory structure

- core - The core Coldfront application
- common - Common code shared between applications
- extra - Extra applications that can be configured in Coldfront

## Developing

yum groupinstall @Development
yum install mariadb-server mariadb-devel redis python36 python36-devel openldap-devel 

Checkout the code, setup virtualenv, and install requirments:
```
$ git clone https://github.com/ubccr/coldfront.git
$ cd coldfront/
$ python3 -mvenv venv
$ source venv/bin/activate
$ pip install -r requirements.txt

```

## License

Coldfront is released under the GPLv3 license. See the LICENSE file.
