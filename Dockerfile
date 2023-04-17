FROM centos/python-38-centos7

LABEL description="coldfront"

USER root
WORKDIR /root
COPY requirements.txt ./
RUN pip install -r requirements.txt && rm requirements.txt
RUN pip install jinja2 pyyaml

# mybrc or mylrc
ARG portal="mybrc"
RUN mkdir -p /var/log/user_portals/cf_${portal} \
 && touch /var/log/user_portals/cf_${portal}/cf_${portal}_{portal,api}.log \
 && chmod 775 /var/log/user_portals/cf_${portal} \
 && chmod 664 /var/log/user_portals/cf_${portal}/cf_${portal}_{portal,api}.log

ARG base_dir="/vagrant/coldfront_app"
COPY . ${base_dir}/coldfront/
WORKDIR ${base_dir}/coldfront/

RUN chmod +x ./manage.py

CMD ./manage.py initial_setup \
 && ./manage.py add_accounting_defaults \
 && ./manage.py add_allowance_defaults \
 && ./manage.py add_directory_defaults \
 && ./manage.py create_allocation_periods \
 && ./manage.py create_staff_group \
 && ./manage.py collectstatic --noinput \
 && ./manage.py runserver 0.0.0.0:80

EXPOSE 80
STOPSIGNAL SIGINT
