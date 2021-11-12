systemctl enable firewalld
service firewalld start

if ! firewall-cmd --list-all-zones | grep -q mybrc_dev
then
    firewall-cmd --new-zone=mybrc_dev --permanent
fi

firewall-cmd --zone=mybrc_dev --add-source=0.0.0.0/0 --permanent
firewall-cmd --zone=mybrc_dev --add-port=80/tcp --permanent
firewall-cmd --zone=mybrc_dev --add-port=22/tcp --permanent
firewall-cmd --reload
