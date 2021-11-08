Vagrant.configure("2") do |config|

  config.vm.box = "Scientific Linux 7 x86_64 Vagrant Base Box"
  config.vm.box_url = "http://scs-repo.lbl.gov/img/rhel/7/sl7.box"
  config.vbguest.auto_update = false

  # Run Ansible from the Vagrant VM
  config.vm.provision "ansible_local" do |ansible|
    ansible.playbook = "bootstrap/development/playbook.yml"
  end

end
