# Redis Container Configuration

This directory is meant to be used in the generation of a redis docker 
container that connects with the coldfront docker container.

The docker container can be created ad-hoc with the following command:

`docker run -d --network coldfront --name coldfront-redis -v 
/srv/coldfront/coldfront/redis/:/usr/local/etc/redis redis:latest /usr/local/etc/redis/redis.conf`

`redis.conf` has its `bind` setting set to the predicted private network IP 
address of its Docker container and `protected-mode` set to `no`. 

