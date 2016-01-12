# ScaleIO Puppet Manifest for Compute Nodes

class install_scaleio_compute
{
  if($::operatingsystem == 'Ubuntu') {
    include install_scaleio_compute::ubuntu
  }else {
    include install_scaleio_compute::centos
  }
}

