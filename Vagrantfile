Vagrant.configure("2") do |config|

  config.vm.box = "Scientific Linux 7 x86_64 Vagrant Base Box"
  config.vm.box_url = "http://scs-repo.lbl.gov/img/rhel/7/sl7.box"
  config.vbguest.auto_update = false

  config.vm.synced_folder ".", "/vagrant/coldfront_app/coldfront"

  config.vm.provision "shell", inline: "/vagrant/coldfront_app/coldfront/bootstrap/development/update_curl.sh", privileged: true
  config.vm.provision "shell", inline: "/vagrant/coldfront_app/coldfront/bootstrap/development/fix_certs.sh", privileged: true

  # Run Ansible from the Vagrant VM
  config.vm.provision "ansible_local" do |ansible|
    ansible.galaxy_role_file = "coldfront_app/coldfront/bootstrap/development/requirements.yml"
    ansible.playbook = "coldfront_app/coldfront/bootstrap/development/playbook.yml"
  end

  config.vm.network :forwarded_port, host: 8880, guest: 80

  config.vm.provider "virtualbox" do |v|
    v.memory = 4096
    v.cpus = 2
  end

end
