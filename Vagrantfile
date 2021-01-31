# zcu-kiv-ds-2

node_first = 1
node_count = 4

ip_address_prefix = "192.168.152."
ip_address_base = 10

port = 55502
service_port = 55512

Vagrant.configure("2") do |config|

  config.vm.box = "debian/buster64"
  config.vm.synced_folder ".", "/vagrant"

  (node_first..node_count).each do |i|
    config.vm.define "node-#{i}" do |node|
      node.vm.hostname = "node-#{i}"
      node.vm.network "private_network", ip: "#{ip_address_prefix}#{ip_address_base + i}"
      node.vm.provision "shell", inline: <<~SHELL
        apt-get update
        apt-get -y install python3-zmq

        mkdir -p /opt/zcu-kiv-ds-2
        cp /vagrant/src/node.py /vagrant/src/get_snapshot.py /opt/zcu-kiv-ds-2/
        cp /vagrant/unit/node.service /etc/systemd/system/
        ln -s /opt/zcu-kiv-ds-2/get_snapshot.py /usr/local/bin/get_snapshot

        config_add() { echo "$1" >> /etc/default/node; }

        config_add "# Node configuration"
        config_add ""
        config_add "NODE_ID=#{i}"
        config_add "NODE_COUNT=#{node_count}"
        config_add "NODE_PORT=#{port}"
        config_add "NODE_SERVICE_PORT=#{service_port}"

        [ #{i} -gt #{node_first} ] && config_add "NODE_PREV_ADDRESS=#{ip_address_prefix}#{ip_address_base + i - 1}:#{port}"
        [ #{i} -lt #{node_count} ] && config_add "NODE_NEXT_ADDRESS=#{ip_address_prefix}#{ip_address_base + i + 1}:#{port}"

        systemctl --now enable node

        adduser vagrant systemd-journal
      SHELL
    end
  end

end
