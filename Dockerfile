FROM centos:8

LABEL description="coldfront"

# install dependencies
RUN yum -y install epel-release
RUN yum -y update
RUN yum -y install python36 python36-devel git memcached redis

WORKDIR /root

# install coldfront
RUN mkdir /opt/coldfront_app

WORKDIR /opt/coldfront_app

RUN cd /opt/coldfront_app
RUN git clone https://github.com/ubccr/coldfront.git
RUN python3.6 -mvenv venv
RUN source venv/bin/activate

WORKDIR /opt/coldfront_app/coldfront

RUN cd /opt/coldfront_app/coldfront
RUN pip3 install wheel
RUN pip3 install -r requirements.txt
RUN cp coldfront/config/local_settings.py.sample coldfront/config/local_settings.py
RUN cp coldfront/config/local_strings.py.sample coldfront/config/local_strings.py

RUN python3 ./manage.py initial_setup
RUN python3 ./manage.py load_test_data

EXPOSE 8000
STOPSIGNAL SIGINT
