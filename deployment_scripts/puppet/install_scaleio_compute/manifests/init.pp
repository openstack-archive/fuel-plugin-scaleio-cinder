# ScaleIO Puppet Manifest for Compute Nodes

class install_scaleio_compute
{
  $nova_service = 'openstack-nova-compute'
  $mdm_ip_1 = $plugin_settings['scaleio_mdm1']
  $mdm_ip_2 = $plugin_settings['scaleio_mdm2']


#install ScaleIO SDC package  
  
  exec { "install_sdc":    
    command => "/bin/bash -c \"MDM_IP=$mdm_ip_1,$mdm_ip_2 yum install -y EMC-ScaleIO-sdc\"",        
    path => "/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin:/root/bin",
  }

  #Configure nova-compute
  ini_subsetting { 'nova-volume_driver':
    ensure  => present,
    path    => '/etc/nova/nova.conf',
    subsetting_separator => ',',
    section => 'libvirt',
    setting => 'volume_drivers',
    subsetting => 'scaleio=nova.virt.libvirt.scaleiolibvirtdriver.LibvirtScaleIOVolumeDriver',
    notify => Service[$nova_service],
  }

  file { 'scaleiolibvirtdriver.py':
    path  => '/usr/lib/python2.6/site-packages/nova/virt/libvirt/scaleiolibvirtdriver.py',
    source => 'puppet:///modules/install_scaleio_compute/scaleiolibvirtdriver.py',
    mode  => '644',
    owner => 'root',
    group => 'root',
    notify => Service[$nova_service],  
  }

  file { 'scaleio.filters':
    path  => '/usr/share/nova/rootwrap/scaleio.filters',
    source => 'puppet:///modules/install_scaleio_compute/scaleio.filters',
    mode  => '644',
    owner => 'root',
    group => 'root',
    notify => Service[$nova_service],
  }

  service { $nova_service:
    ensure => 'running',
  }
}

