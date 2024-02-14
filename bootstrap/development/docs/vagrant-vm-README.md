# Vagrant VM (VirtualBox) Development Environment

<b>Note: There are known issues with running VirtualBox on Apple Silicon. Use the Docker option instead.</b>

The application may be installed within a Vagrant VM that is running on Scientific Linux 7. The VM is provisioned using the same Ansible playbook used in production.

## Initial Setup

1. Install [VirtualBox](https://www.virtualbox.org/).
2. Clone the repository.
   ```
   git clone https://github.com/ucb-rit/coldfront.git
   cd coldfront
   ```
3. Prevent Git from detecting changes to file permissions.
   ```
   git config core.fileMode false
   ```
4. Checkout the desired branch (probably `develop`).
5. Install [vagrant-vbguest](https://github.com/dotless-de/vagrant-vbguest).
   ```
   vagrant plugin install vagrant-vbguest
   ```
6. Create a `main.yml` file in the top-level of the repository. This is a file of variables used by Ansible to configure the system.
   ```
   cp bootstrap/ansible/main.copyme main.yml
   ```
7. Generate a key to be used as the `SECRET_KEY` for Django.
   ```
   # This produces two lines: condense them into one.
   openssl rand -base64 64
   ```
8. Customize `main.yml`. In particular, uncomment everything under the `dev_settings` section, and fill in the below variables. Note that quotes need not be provided, except in the list variable.
   ```
   django_secret_key: secret_key_from_previous_step
   db_admin_passwd: password_here
   redis_passwd: password_here
   from_email: you@email.com
   admin_email: you@email.com
   email_admin_list: ["you@email.com"]
   request_approval_cc_list: ["you@email.com"]
   ```
9. Provision the VM. This should run the Ansible playbook. Expect this to take a few minutes on the first run.
   ```
   vagrant up
   ```
10. SSH into the VM.
   ```
   vagrant ssh
   ```
11. On the host machine, navigate to `http://localhost:8880`, where the application should be served.
12. (Optional) Load data from a database dump file.
    ```
    # Clear the Django database to avoid conflicts.
    python manage.py sqlflush | python manage.py dbshell
    # Load from the dump file (use the -k option if the command errors because database is being accessed).
    sh bootstrap/development/load_database_backup.sh [-k] DB_NAME /absolute/path/to/dump.file
    # Set user passwords.
    python manage.py set_passwords --password <password>
    ```


## Virtual Machine

- Once the VM has been provisioned the first time, starting and accessing it can be done with:
  ```
  vagrant up
  vagrant ssh
  ```

- To stop the VM, run:
  ```
  vagrant halt
  ```

- To re-provision the VM, run:
  ```
  vagrant provision
  ```

## Environment

- The application is served via Apache, so any changes to the application (excluding changes to templates) are not applied until Apache is restarted, which can be done with:
  ```
  sudo systemctl restart httpd
  ```
- The Ansible playbook can be run manually as follows.
  ```
  cd /vagrant/coldfront_app/coldfront
  # Assert that there is a properly-configured main.yml in the current directory.
  ansible-playbook bootstrap/ansible/playbook.yml
  ```
  - Note that to skip initial provisioning tasks you can use the `--tags common` or `--skip-tags provisioning` arguments to `ansible-playbook`.
  - Alternatively, you can set `provisioning_tasks` to `False` in `main.yml`

- Any custom Django settings can be applied by modifying `dev_settings.py`. Note that running the Ansible playbook will overwrite these.

## Emails

- By default, emails are configured to be sent via SMTP on port 1025. If no such server is running on that port, many operations will fail. To start a server, start a separate SSH session (`vagrant ssh`), and run the below. All emails will be outputted here for inspection.
  ```
  python -m smtpd -n -c DebuggingServer localhost:1025
  ```
