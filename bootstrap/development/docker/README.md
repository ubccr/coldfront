## Docker Development Environment

Note that these steps must be run from the root directory of the repo.

1. Build Docker images.

   ```bash
   sh bootstrap/development/docker/scripts/build_images.sh
   ```

2. Retrieve a `cilogon.yml` file containing CILogon credentials that will be provided for you. Place it in the Docker configuration directory.

   ```bash
   mv /path/to/cilogon.yml bootstrap/development/docker/config
   ```

3. Generate secrets, such as passwords for PostgreSQL and Redis.

   ```bash
   sh bootstrap/development/docker/scripts/docker_generate_secrets.sh
   ```

   Notes:
     - This step should only be performed once. Running it again will overwrite existing passwords that may already have been used to configure services.

4. Generate Django settings files using values defined in the Docker configuration directory. You must provide a deployment name ("BRC" or "LRC").

   ```bash
   export DEPLOYMENT=BRC
   sh bootstrap/development/docker/scripts/docker_generate_settings.sh $DEPLOYMENT
   ```

   Notes:
     - This step may be performed multiple times.
     - The `main.yml` file does not need to be modified in any way, despite indications within it. Its pre-defined values will be overridden and added to based on the other YML files in the directory.

5. Generate a `.env` file with environment variables that will be passed to `docker-compose.yml`. You must provide a deployment name ("BRC" or "LRC"), as well as a port where the web service will be available ("8880", "8881", "8882", or "8883").

   ```bash
   export WEB_PORT=8880
   sh bootstrap/development/docker/scripts/create_env_file.sh $DEPLOYMENT $WEB_PORT
   ```

   Notes:
     - `docker-compose.yml` looks for a `.env` file in the same directory it resides in. This script creates `.env` there.
     - The port must be one of the above because the CILogon application client is only configured for one of those four ports.
     - The port may be customized so that multiple instances may run at the same time, without port clashes.

6. Start the application stack. Specify a unique Docker project name so that resources are placed within a Docker namespace. Examples: "brc-dev", "lrc-dev".

   ```bash
   export DOCKER_PROJECT_NAME=brc-dev
   docker-compose \
       -f bootstrap/development/docker/docker-compose.yml \
       -p $DOCKER_PROJECT_NAME \
       up
   ```

7. Run Django scripts to set up the database and perform other tasks. You must provide the name of your Docker project.

   ```bash
   sh bootstrap/development/docker/scripts/docker_run_django_scripts.sh $DOCKER_PROJECT_NAME
   ```

   Notes:
     - This step may be run multiple times.

8. Retrieve a PostgreSQL database dump file that will be provided for you. Place it in the root directory of the repo. Load it into your instance. You must provide the name of your Docker project.

   ```bash
   export RELATIVE_CONTAINER_DUMP_FILE_PATH=YYYY_MM_DD-HH-MM.dump
   sh bootstrap/development/docker/scripts/docker_load_database_backup.sh $DOCKER_PROJECT_NAME $RELATIVE_CONTAINER_DUMP_FILE_PATH
   ```

9. At this point, the web service should be functioning. Navigate to it from the browser at "http://localhost:WEB_PORT", where `WEB_PORT` is the one defined above.

10. After authenticating for the first time, grant your user administrator privileges in Django:

    - Enter into the application shell container:

         ```bash
         docker-compose -p $DOCKER_PROJECT_NAME exec app-shell bash
         ```

    - From within the container, start a Django shell:

         ```bash
         python3 manage.py shell
         ```

    - From within the Django shell, update your user:

         ```python
         from django.contrib.auth.models import User

         # The username is the string that appears on the right-hand side of the
         # menu. It will be an email address if you do not have a cluster account.
         user = User.objects.get(username="your_username")
         user.is_staff = True
         user.is_superuser = True
         user.save()
         ```
