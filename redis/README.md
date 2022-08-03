# Redis Container Configuration

This directory is meant to be used in the generation of a redis docker 
container that connects with the coldfront docker container.

The docker container can be created ad-hoc with the following command:

`docker run -d --network coldfront --name coldfront-redis -v 
/srv/coldfront/coldfront/redis/:/usr/local/etc/redis redis:latest /usr/local/etc/redis/redis.conf`

`redis.conf` has its `bind` setting set to the predicted private network IP 
address of its Docker container and `protected-mode` set to `no`. 

For Coldfront to recognize the separate redis Docker container, add the following
to local_settings.py:

```python
#------------------------------------------------------------------------------
# Django Q settings
#------------------------------------------------------------------------------
Q_CLUSTER = {
    'name': 'coldfront-redis',
    'workers': 8,
    'recycle': 500,
    'timeout': 60,
    'compress': True,
    'save_limit': 250,
    'queue_limit': 500,
    'cpu_affinity': 1,
    'label': 'Django Q',
    'redis': {
                'host': 'coldfront-redis',
                'port': 6379,
                'db': 0, }
    # 'redis': redis_conf(REDIS.get('default', {})),
}
```
