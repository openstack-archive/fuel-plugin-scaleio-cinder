class install_scaleio_controller
{
  if($::operatingsystem == 'Ubuntu') {
    include install_scaleio_controller::ubuntu
  }else {
    include install_scaleio_controller::centos
  }
}


