# A root certificate (DST Root CA X3) expired on September 30th, 2021,
# but it will not be removed until 2024. Blacklist it so that SSL
# behaves properly.
# Source: https://blog.devgenius.io/rhel-centos-7-fix-for-lets-encrypt-change-8af2de587fe4
# Source: https://access.redhat.com/errata/RHBA-2021:3649

# Upgrading to ca-certificates 2021.2.50-72 should fix the issue.
yum update -y -q ca-certificates
update-ca-trust

# Upgrade Python to resolve SSL issues.
yum install -y -q python
