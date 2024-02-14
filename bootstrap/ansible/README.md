# Deployment

## Ansible

Deployments and configuration management are handled by Ansible, located in the `bootstrap/ansible` directory.

In particular, the Ansible playbook installs, enables, and configures PostgreSQL and Redis, creates log files, installs Pip requirements, copies ColdFront settings files, runs initial setup, migrates the database, collects static files, creates WSGI files for Apache, and restarts Apache.

Note that there are some additional server setup steps that are not currently captured in the Ansible playbook.

Also note that on production environments you must install necessary Ansible
collections using `ansible-galaxy collection install -r bootstrap/ansible/requirements.yml` before initially running the playbook.

1. Create `main.yml`.

    ```
    cp bootstrap/ansible/main.copyme main.yml
    ```

2. Modify `main.yml` depending on the current deployment.

3. Run the Ansible playbook as the `djangooperator` user defined in `main.yml`.

```
ansible-playbook bootstrap/ansible/playbook.yml
```

## Dynamic Settings

Some configuration may need to be updated without a server restart (e.g., links to external resources). Such configuration is managed by `django-constance` and stored in Redis. To update these, navigate to the URL path `/admin/constance/config/`, and set the correct values for the current deployment.
