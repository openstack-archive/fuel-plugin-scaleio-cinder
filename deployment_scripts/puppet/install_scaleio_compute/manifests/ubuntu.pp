# ScaleIO Puppet Manifest for Compute Nodes Ubuntu

class install_scaleio_compute::ubuntu
{
  $nova_service = 'nova-compute'
  $mdm_ip_1 = $plugin_settings['scaleio_mdm1']
  $mdm_ip_2 = $plugin_settings['scaleio_mdm2']

#install ScaleIO SDC package

  # file { 'emc-scaleio-sdc.deb':
  #  path  => '/tmp/emc-scaleio-sdc.deb',
  #  source => 'puppet:///modules/install_scaleio_compute/emc.deb',
  #  mode  => '644',
  #  owner => 'root',
  #  group => 'root',
 # }->

 #exec {"Install sdc":
 #   command => "bash -c 'dpkg -i /tmp/emc-scaleio-sdc.deb'",
 #   path    => ['/usr/bin', '/bin','/usr/local/sbin','/usr/sbin','/sbin' ],
 #}->

package{'emc-scaleio-sdc':
 ensure => installed,
}->
 exec {"Add MDM to drv-cfg":
    command => "bash -c 'echo mdm ${mdm_ip_1},${mdm_ip_2}  >> /bin/emc/scaleio/drv_cfg.txt'",
    path    =>  ['/usr/bin', '/bin','/usr/local/sbin','/usr/sbin','/sbin' ],
 }->


 exec {"Start SDC":
    command => "bash -c '/etc/init.d/scini restart'",
    path    =>  ['/usr/bin', '/bin','/usr/local/sbin','/usr/sbin','/sbin' ],
 }->

  
  
  #Configure nova-compute
  ini_subsetting { 'nova-volume_driver':
    ensure  => present,
    path    => '/etc/nova/nova.conf',
    subsetting_separator => ',',
    section => 'libvirt',
    setting => 'volume_drivers',
    subsetting => 'scaleio=nova.virt.libvirt.scaleiolibvirtdriver.LibvirtScaleIOVolumeDriver',
    notify => Service[$nova_service],
  }->
  
if(hiera('fuel_version') == '6.1') {
  file { 'scaleiolibvirtdriver.py':
    path  => '/usr/lib/python2.7/dist-packages/nova/virt/libvirt/scaleiolibvirtdriver.py',
    source => 'puppet:///modules/install_scaleio_compute/6.1/scaleiolibvirtdriver.py',
    mode  => '644',
    owner => 'root',
    group => 'root',
    notify => Service[$nova_service],
  }
  }else{
	  file { 'driver.py':
		path  => '/usr/lib/python2.7/dist-packages/nova/virt/libvirt/driver.py',
		source => 'puppet:///modules/install_scaleio_compute/7.0/driver.py',
		mode  => '644',
		owner => 'root',
		group => 'root',
		notify => Service[$nova_service],  
	  } ->
	  file { 'volume.py':
		path  => '/usr/lib/python2.7/dist-packages/nova/virt/libvirt/volume.py',
		source => 'puppet:///modules/install_scaleio_compute/7.0/volume.py',
		mode  => '644',
		owner => 'root',
		group => 'root',
		notify => Service[$nova_service],  
	  } 
  }->
  

  file { 'scaleio.filters':
    path  => '/etc/nova/rootwrap.d/scaleio.filters',
    source => 'puppet:///modules/install_scaleio_compute/scaleio.filters',
    mode  => '644',
    owner => 'root',
    group => 'root',
    notify => Service[$nova_service],
  }~>

  service { $nova_service:
    ensure => 'running',
  }
}

