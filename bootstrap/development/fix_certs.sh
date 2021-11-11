# A root certificate (DST Root CA X3) expired on September 30th, 2021,
# but it will not be removed until 2024. Blacklist it so that SSL
# behaves properly.
# Source: https://blog.devgenius.io/rhel-centos-7-fix-for-lets-encrypt-change-8af2de587fe4
# Source: https://access.redhat.com/errata/RHBA-2021:3649

# Upgrading to ca-certificates 2021.2.50-72 should fix the issue.
yum update ca-certificates
update-ca-trust

# If it doesn't, blacklist the certificate anyway.
trust dump --filter "pkcs11:id=%c4%a7%b1%a4%7b%2c%71%fa%db%e1%4b%90%75%ff%c4%15%60%85%89%10" |
	openssl x509 |
	sudo tee /etc/pki/ca-trust/source/blacklist/DST-Root-CA-X3.pem
sudo update-ca-trust extract
