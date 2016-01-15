class install_scaleio_controller::centos
{
   $services = ['openstack-cinder-volume', 'openstack-cinder-api', 'openstack-cinder-scheduler', 'openstack-nova-scheduler']

  $gw_ip = $plugin_settings['scaleio_GW']
  $mdm_ip_1 = $plugin_settings['scaleio_mdm1']
  $mdm_ip_2 = $plugin_settings['scaleio_mdm2']
  $admin =  $plugin_settings['scaleio_Admin']
  $password = $plugin_settings['scaleio_Password']
  $volume_type = "scaleio-thin" 
#1. Install SDC package
  exec { "install_sdc1":    
    command => "/bin/bash -c \"MDM_IP=$mdm_ip_1,$mdm_ip_2 yum install -y EMC-ScaleIO-sdc\"",
    path => "/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin:/root/bin",
  } ->
#2. Copy ScaleIO Files
  file { 'scaleio.py':
    path => '/usr/lib/python2.6/site-packages/cinder/volume/drivers/emc/scaleio.py',
    source => 'puppet:///modules/install_scaleio_controller/6.1/scaleio.py',
    mode  => '644',
    owner => 'root',
    group => 'root',
  } ->

  file { 'scaleio.filters':
    path => '/usr/share/cinder/rootwrap/scaleio.filters',
    source => 'puppet:///modules/install_scaleio_controller/scaleio.filters',
    mode  => '644',
    owner => 'root',
    group => 'root',
    before => File['cinder_scaleio.config'], 
  }

# 3. Create config for ScaleIO
  $cinder_scaleio_config = "[scaleio]
rest_server_ip=$gw_ip
rest_server_username=$admin
rest_server_password=$password
protection_domain_name=${plugin_settings['protection_domain']}
storage_pools=${plugin_settings['protection_domain']}:${plugin_settings['storage_pool_1']}
storage_pool_name=${plugin_settings['storage_pool_1']}
round_volume_capacity=True
force_delete=True
verify_server_certificate=False
"

  file { 'cinder_scaleio.config':
    ensure  => present,
    path  => '/etc/cinder/cinder_scaleio.config',
    content => $cinder_scaleio_config,
    mode  => 0644,
    owner => root,
    group => root,
    before => Ini_setting['cinder_conf_enabled_backeds'],
  } ->

  # 4. To /etc/cinder/cinder.conf add
  ini_setting { 'cinder_conf_enabled_backeds':
    ensure  => present,
    path    => '/etc/cinder/cinder.conf',
    section => 'DEFAULT',
    setting => 'enabled_backends',
    value => 'ScaleIO',
    before => Ini_setting['cinder_conf_volume_driver'],
  } ->
  ini_setting { 'cinder_conf_volume_driver':
    ensure  => present,
    path    => '/etc/cinder/cinder.conf',
    section => 'ScaleIO',
    setting => 'volume_driver',
    value => 'cinder.volume.drivers.emc.scaleio.ScaleIODriver',
    before => Ini_setting['cinder_conf_scio_config'],
  } ->
  ini_setting { 'cinder_conf_scio_config':
    ensure  => present,
    path    => '/etc/cinder/cinder.conf',
    section => 'ScaleIO',
    setting => 'cinder_scaleio_config_file',
    value => '/etc/cinder/cinder_scaleio.config',
	before => Ini_setting['cinder_conf_volume_backend_name'],
  } ->
  ini_setting { 'cinder_conf_volume_backend_name':
    ensure  => present,
    path    => '/etc/cinder/cinder.conf',
    section => 'ScaleIO',
    setting => 'volume_backend_name',
    value => 'ScaleIO',
  }~>
  service { $services:
    ensure => running,
  }->
    exec { "Create Cinder volume type \'${volume_type}\'":
    command => "bash -c 'source /root/openrc; cinder type-create ${volume_type}'",
    path    => ['/usr/bin', '/bin'],
    unless  => "bash -c 'source /root/openrc; cinder type-list |grep -q \" ${volume_type} \"'",
  } ->

  exec { "Create Cinder volume type extra specs for \'${volume_type}\'":
    command => "bash -c 'source /root/openrc; cinder type-key ${volume_type} set sio:pd_name=${plugin_settings['protection_domain']} sio:provisioning=thin sio:sp_name=${plugin_settings['storage_pool_1']}'",
    path    => ['/usr/bin', '/bin'],
    onlyif  => "bash -c 'source /root/openrc; cinder type-list |grep -q \" ${volume_type} \"'",
  }

}
